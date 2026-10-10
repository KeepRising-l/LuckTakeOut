"""AI 工具集：函数定义（供大模型调用）+ 本地实现。

所有工具都由后端执行，模型只负责"理解与组织参数"。
每次调用都会写入操作审计（operation_log），actor_role = 'ai'。
"""

import json
from decimal import Decimal

from django.db.models import Q

from merchant.models import MerchantInfo
from order.models import OrderInfo, OrderStatusLog, UrgeRecord
from platform_ops.models import Notification, OperationLog
from product.models import ProductInfo, ProductSku
from review.models import Review

from .models import OrderDraft, OrderDraftItem

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
    _fn('get_item_specs', '获取某个菜品的规格与价格', {'product_id': {'type': 'integer'}}, ['product_id']),
    _fn('validate_draft', '后端校验草稿：价格、库存、商户归属', {
        'merchant_id': {'type': 'integer'},
        'items': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'product_id': {'type': 'integer'},
                    'sku_id': {'type': 'integer'},
                    'quantity': {'type': 'integer'},
                },
            },
        },
    }, ['merchant_id', 'items']),
    _fn('create_draft', '生成待确认订单草稿（不产生正式订单）', {
        'merchant_id': {'type': 'integer'},
        'items': {'type': 'array', 'items': {'type': 'object'}},
        'address_id': {'type': 'integer'},
    }, ['merchant_id', 'items']),
    _fn('get_order_status', '查询订单当前状态与骑手', {'order_id': {'type': 'integer'}}),
    _fn('urge_order', '对该订单发起催单（通知商户/骑手）', {
        'order_id': {'type': 'integer'},
        'content': {'type': 'string'},
    }, ['order_id']),
    _fn('submit_review', '对已完成订单提交评价', {
        'order_id': {'type': 'integer'},
        'rating': {'type': 'integer'},
        'content': {'type': 'string'},
    }, ['order_id', 'rating']),
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
        actor_id=session.cs_user_id, actor_role='ai',
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


def t_get_item_specs(session, args):
    product_id = args.get('product_id')
    p = ProductInfo.objects.filter(id=product_id).first()
    if not p:
        return {'skus': [], 'error': '菜品不存在'}
    skus = [{'id': s.id, 'spec_text': s.spec_text, 'price': float(s.price), 'stock': s.stock}
            for s in p.skus.all()]
    if not skus:
        skus = [{'id': None, 'spec_text': '默认', 'price': float(p.price), 'stock': p.stock}]
    _audit(session, 'get_item_specs', 'product', product_id, json.dumps(args, ensure_ascii=False))
    return {'product_id': p.id, 'name': p.name, 'skus': skus}


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
            'product_id': p.id, 'sku_id': it.get('sku_id'),
            'product_name': p.name, 'price': float(p.price),
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
        p = ProductInfo.objects.filter(id=it.get('product_id'), merchant=merchant).first()
        if not p:
            continue
        qty = int(it.get('quantity') or 1)
        total += p.price * qty
        sku = ProductSku.objects.filter(id=it.get('sku_id')).first()
        resolved.append((p, sku, qty))

    draft = OrderDraft.objects.create(
        session=session, customer=session.customer, merchant=merchant,
        address=address, total_amount=total, status=OrderDraft.STATUS_PENDING,
    )
    for p, sku, qty in resolved:
        OrderDraftItem.objects.create(
            draft=draft, product=p, sku=sku,
            spec_text=(sku.spec_text if sku else ''), quantity=qty, price_snapshot=p.price,
        )
    result = {
        'draftId': draft.id,
        'merchantName': merchant.name,
        'total': float(total),
        'address': (address.detail if address else ''),
        'items': [{'name': p.name, 'quantity': q, 'price': float(p.price)} for p, _, q in resolved],
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


def t_urge_order(session, args):
    o = _resolve_order(session, args.get('order_id'))
    if not o:
        return {'error': '没有找到订单'}
    content = args.get('content') or '顾客催单'
    UrgeRecord.objects.create(order=o, operator_id=session.cs_user_id, operator_role='ai', content=content)
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
    rating = int(args.get('rating') or 5)
    Review.objects.create(
        order=o, user=session.customer, merchant=o.merchant,
        target_type=Review.TARGET_MERCHANT, rating=rating,
        content=args.get('content') or '',
    )
    _audit(session, 'submit_review', 'order', o.id, json.dumps(args, ensure_ascii=False))
    return {'ok': True, 'message': '评价已提交'}


DISPATCH = {
    'search_merchant': t_search_merchant,
    'search_menu': t_search_menu,
    'get_item_specs': t_get_item_specs,
    'validate_draft': t_validate_draft,
    'create_draft': t_create_draft,
    'get_order_status': t_get_order_status,
    'urge_order': t_urge_order,
    'submit_review': t_submit_review,
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
