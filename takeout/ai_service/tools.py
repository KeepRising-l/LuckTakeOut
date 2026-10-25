"""AI 工具集：函数定义（供大模型调用）+ 本地实现。

所有工具都由后端执行，模型只负责"理解与组织参数"。
每次调用都会写入操作审计（operation_log），actor_role = 'ai'。
"""

import json
from decimal import Decimal

from django.db.models import Q

from merchant.models import MerchantInfo
from order.models import OrderInfo, OrderStatusLog, UrgeRecord
from order.services import apply_refund_for_order
from platform_ops.models import Notification, OperationLog
from product.models import ProductInfo
from review.models import Review

from .models import OrderDraft, OrderDraftItem
from .recommend import build_profile, recommend_dishes

ORDER_STATUS_TEXT = {
    10: '待支付', 20: '已支付', 30: '待接单', 40: '配送中',
    50: '已完成', 60: '已取消', 70: '退款中', 80: '已退款',
}


# ---- 函数定义（OpenAI 兼容格式）----

def _fn(name, desc, props, required=None):
    return {
        'type': 'function',
        'function': {
            'name': name,
            'description': desc,
            'parameters': {
                'type': 'object',
                'properties': props,
                'required': required or [],
            },
        },
    }


TOOL_SCHEMAS = [
    _fn('search_merchant', '按关键词搜索商户', {'keyword': {'type': 'string', 'description': '商户名称关键词'}}),
    _fn('search_menu', '查询某商户的菜品', {
        'merchant_id': {'type': 'integer'},
        'keyword': {'type': 'string'},
    }, ['merchant_id']),
    _fn('validate_draft', '后端校验草稿：价格、库存、商户归属', {
        'merchant_id': {'type': 'integer'},
        'items': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'product_id': {'type': 'integer'},
                    'quantity': {'type': 'integer'},
                },
            },
        },
    }, ['merchant_id', 'items']),
    _fn('create_draft', '生成待确认订单草稿（不产生正式订单）', {
        'merchant_id': {'type': 'integer'},
        'items': {'type': 'array', 'items': {'type': 'object'}},
        'address_id': {'type': 'integer'},
        'remark': {'type': 'string', 'description': '订单备注，如「不要香菜」「多加醋」'},
    }, ['merchant_id', 'items']),
    _fn('get_order_status', '查询订单当前状态与骑手', {'order_id': {'type': 'integer'}}),
    _fn('apply_refund', '对本人订单申请全额退款（仅已支付/待接单可申请，提交后由商户审核）', {
        'order_id': {'type': 'integer', 'description': '订单号，不传或传 0 则用最近一笔订单'},
        'reason': {'type': 'string', 'description': '退款原因'},
    }, []),
    _fn('urge_order', '对该订单发起催单（通知商户/骑手）', {
        'order_id': {'type': 'integer'},
        'content': {'type': 'string'},
    }, ['order_id']),
    _fn('submit_review', '对已完成订单提交评价', {
        'order_id': {'type': 'integer'},
        'rating': {'type': 'integer'},
        'content': {'type': 'string'},
    }, ['order_id', 'rating']),
    _fn('get_my_history', '查看当前顾客的历史点餐偏好（常点商户、常点菜品、客单价、常点时段）',
        {}, []),
    _fn('recommend_dishes', '基于顾客历史偏好推荐菜品，每条带推荐理由', {
        'limit': {'type': 'integer', 'description': '返回条数，默认 6'},
    }, []),
]


# ---- 辅助 ----

def _latest_order(session):
    return OrderInfo.objects.filter(user=session.customer).order_by('-id').first()


def _resolve_order(session, order_id):
    if order_id:
        return OrderInfo.objects.filter(id=order_id, user=session.customer).first()
    return _latest_order(session)


def _audit(session, action, target_type, target_id, detail, result='success'):
    OperationLog.objects.create(
        actor_id=session.customer_id, actor_role='ai',
        action=action, target_type=target_type, target_id=target_id,
        detail=detail, result=result,
    )


# ---- 工具实现 ----

def t_search_merchant(session, args):
    kw = (args.get('keyword') or '').strip()
    qs = MerchantInfo.objects.filter(status=20)
    if kw:
        qs = qs.filter(Q(name__icontains=kw) | Q(description__icontains=kw))
    result = {'list': [{'id': m.id, 'name': m.name} for m in qs[:10]]}
    _audit(session, 'search_merchant', 'merchant', None, json.dumps(args, ensure_ascii=False))
    return result


def t_search_menu(session, args):
    merchant_id = args.get('merchant_id')
    qs = ProductInfo.objects.filter(merchant_id=merchant_id, status=10)
    kw = (args.get('keyword') or '').strip()
    if kw:
        qs = qs.filter(name__icontains=kw)
    result = {'list': [{'id': p.id, 'name': p.name, 'price': float(p.price)} for p in qs[:30]]}
    _audit(session, 'search_menu', 'merchant', merchant_id, json.dumps(args, ensure_ascii=False))
    return result


def t_validate_draft(session, args):
    """后端重校验：以数据库中的价格、库存、商户归属为准。"""
    merchant = MerchantInfo.objects.filter(id=args.get('merchant_id'), status=20).first()
    if not merchant:
        return {'valid': False, 'message': '商户不存在或未通过审核'}
    items = []
    total = Decimal('0')
    for it in (args.get('items') or []):
        p = ProductInfo.objects.filter(id=it.get('product_id'), merchant=merchant, status=10).first()
        if not p:
            return {'valid': False, 'message': '存在无效的菜品'}
        qty = int(it.get('quantity') or 0)
        if qty <= 0:
            return {'valid': False, 'message': '数量非法'}
        if p.stock < qty:
            return {'valid': False, 'message': f'「{p.name}」库存不足'}
        amount = p.price * qty
        total += amount
        items.append({
            'product_id': p.id, 'product_name': p.name, 'price': float(p.price),
            'quantity': qty, 'amount': float(amount),
        })
    if not items:
        return {'valid': False, 'message': '草稿内容为空'}
    result = {'valid': True, 'items': items, 'total': float(total)}
    _audit(session, 'validate_draft', 'merchant', merchant.id, json.dumps(args, ensure_ascii=False))
    return result


def t_create_draft(session, args):
    merchant = MerchantInfo.objects.filter(id=args.get('merchant_id'), status=20).first()
    if not merchant:
        return {'error': '商户不存在'}
    address = None
    if args.get('address_id'):
        address = session.customer.addresses.filter(id=args['address_id']).first()
    if address is None:
        address = session.customer.addresses.order_by('-is_default', '-id').first()

    total = Decimal('0')
    resolved = []
    for it in (args.get('items') or []):
        # 只收在售菜品；数量必须为正整数，防止模型参数异常造出负金额草稿
        p = ProductInfo.objects.filter(id=it.get('product_id'), merchant=merchant, status=10).first()
        if not p:
            continue
        try:
            qty = int(it.get('quantity') or 1)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue
        total += p.price * qty
        resolved.append((p, qty))
    if not resolved:
        return {'error': '草稿内容为空或菜品均不可售'}

    draft = OrderDraft.objects.create(
        session=session, customer=session.customer, merchant=merchant,
        address=address, total_amount=total, status=OrderDraft.STATUS_PENDING,
        remark=(args.get('remark') or '').strip()[:255],
    )
    for p, qty in resolved:
        OrderDraftItem.objects.create(
            draft=draft, product=p, quantity=qty, price_snapshot=p.price,
        )
    result = {
        'draftId': draft.id,
        'merchantName': merchant.name,
        'total': float(total),
        'address': (address.detail if address else ''),
        'remark': draft.remark,
        'items': [{'name': p.name, 'quantity': q, 'price': float(p.price)} for p, q in resolved],
    }
    _audit(session, 'create_draft', 'order_draft', draft.id, json.dumps(result, ensure_ascii=False))
    return result


def t_get_order_status(session, args):
    o = _resolve_order(session, args.get('order_id'))
    if not o:
        return {'error': '没有找到订单'}
    result = {
        'orderId': o.id, 'orderNo': o.order_no,
        'status': o.status, 'statusText': ORDER_STATUS_TEXT.get(o.status, ''),
        'riderName': o.rider.name if o.rider else '',
    }
    _audit(session, 'get_order_status', 'order', o.id, json.dumps(args, ensure_ascii=False))
    return result


def t_apply_refund(session, args):
    """申请退款：与顾客端 HTTP 接口共用同一套状态校验（apply_refund_for_order）。"""
    o = _resolve_order(session, args.get('order_id'))
    if not o:
        return {'error': '没有找到订单'}
    ok_flag, message, refund = apply_refund_for_order(
        o.id, session.customer, args.get('reason') or '', operator_role='ai',
    )
    _audit(session, 'apply_refund', 'order', o.id,
           json.dumps(args, ensure_ascii=False), result='success' if ok_flag else 'fail')
    if not ok_flag:
        return {'ok': False, 'message': message}
    return {
        'ok': True, 'message': message, 'refundId': refund.id,
        'orderNo': o.order_no, 'amount': float(refund.amount),
    }


def t_urge_order(session, args):
    o = _resolve_order(session, args.get('order_id'))
    if not o:
        return {'error': '没有找到订单'}
    content = args.get('content') or '顾客催单'
    UrgeRecord.objects.create(order=o, operator_id=session.customer_id, operator_role='ai', content=content)
    Notification.objects.create(
        to_user=o.merchant.auth_user, title='订单催单提醒',
        content=f'订单 {o.order_no}：{content}', type=Notification.TYPE_URGE,
    )
    if o.rider:
        Notification.objects.create(
            to_user=o.rider.auth_user, title='配送催单提醒',
            content=f'订单 {o.order_no}：{content}', type=Notification.TYPE_URGE,
        )
    _audit(session, 'urge_order', 'order', o.id, json.dumps(args, ensure_ascii=False))
    return {'ok': True, 'message': f'已对订单 {o.order_no} 发起催单'}


def t_submit_review(session, args):
    o = _resolve_order(session, args.get('order_id'))
    if not o:
        return {'error': '没有找到订单'}
    if o.status != OrderInfo.STATUS_FINISHED:
        return {'ok': False, 'message': '订单尚未完成，暂不能评价'}
    if Review.objects.filter(order=o).exists():
        return {'ok': False, 'message': '该订单已评价过'}
    # 与顾客端评价接口同口径：评分钳制到 1-5
    rating = min(5, max(1, int(args.get('rating') or 5)))
    Review.objects.create(
        order=o, user=session.customer, merchant=o.merchant,
        target_type=Review.TARGET_MERCHANT, rating=rating,
        content=(args.get('content') or '')[:255],
    )
    _audit(session, 'submit_review', 'order', o.id, json.dumps(args, ensure_ascii=False))
    return {'ok': True, 'message': '评价已提交'}


def t_get_my_history(session, args):
    """返回顾客的口味画像：常点商户、常点菜品、客单价、常点时段。"""
    profile = build_profile(session.customer)
    _audit(session, 'get_my_history', 'customer', session.customer_id, '')
    return profile


def t_recommend_dishes(session, args):
    """基于历史偏好推荐菜品，每条带 reason（可解释）。"""
    try:
        limit = int(args.get('limit') or 6)
    except (TypeError, ValueError):
        limit = 6
    dishes = recommend_dishes(session.customer, limit=max(1, min(limit, 10)))
    _audit(session, 'recommend_dishes', 'customer', session.customer_id,
           json.dumps(args, ensure_ascii=False))
    return {'list': dishes}


DISPATCH = {
    'search_merchant': t_search_merchant,
    'search_menu': t_search_menu,
    'validate_draft': t_validate_draft,
    'create_draft': t_create_draft,
    'get_order_status': t_get_order_status,
    'apply_refund': t_apply_refund,
    'urge_order': t_urge_order,
    'submit_review': t_submit_review,
    'get_my_history': t_get_my_history,
    'recommend_dishes': t_recommend_dishes,
}


def execute_tool(name, args, session):
    handler = DISPATCH.get(name)
    if handler is None:
        return {'error': f'未知工具: {name}'}
    try:
        return handler(session, args)
    except Exception as e:  # noqa: BLE001
        _audit(session, name, 'unknown', None, str(e), result='fail')
        return {'error': str(e)}
