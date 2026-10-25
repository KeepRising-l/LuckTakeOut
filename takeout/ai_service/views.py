"""AI 点餐助手接口：会话、对话、草稿查看与确认。

AI 助手代表当前登录的顾客，因此这里与其它顾客端接口共用同一套令牌认证，
并以登录态反查出的顾客作为会话、消息与草稿的作用域来源。
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from common.auth import api_login_required
from common.response import fail, ok
from common.utils import get_json
from order.models import OrderInfo, OrderItem, OrderStatusLog
from payment.models import PaymentRecord
from product.models import ProductInfo
from user.models import UserInfo

from .agent import run_agent
from .models import ChatSession, OrderDraft, OrderDraftItem
from .recommend import build_profile, build_reorder, recommend_dishes


def _current_customer(request):
    """从登录态反查顾客资料。作用域的唯一可信来源，不读请求体里的顾客标识。"""
    return UserInfo.objects.filter(auth_user=request.user).first()


def draft_to_dict(d):
    return {
        'draftId': d.id,
        'customer': d.customer.nickname,
        'merchant': d.merchant.name,
        'address': d.address.detail if d.address else '',
        'total': float(d.total_amount),
        'status': d.status,
        'items': [
            {
                'name': it.product.name,
                'quantity': it.quantity,
                'price': float(it.price_snapshot),
            }
            for it in d.items.all()
        ],
    }


@require_http_methods(['POST'])
@api_login_required
def create_session(request):
    customer = _current_customer(request)
    if customer is None:
        return fail('用户不存在', status=401)
    session = ChatSession.objects.create(customer=customer, status=10)
    return ok({
        'sessionId': session.id,
        'customerId': customer.id,
        'customerName': customer.nickname,
    })


@require_http_methods(['POST'])
@api_login_required
def chat(request):
    data = get_json(request)
    message = (data.get('message') or '').strip()
    if not message:
        return fail('消息不能为空')

    customer = _current_customer(request)
    if customer is None:
        return fail('用户不存在', status=401)

    session = ChatSession.objects.filter(id=data.get('sessionId'), customer=customer).first()
    if not session:
        return fail('会话不存在，请先创建会话')

    try:
        reply = run_agent(session, message)
    except Exception as e:  # noqa: BLE001
        return fail(f'AI 服务调用失败：{e}')
    draft = session.drafts.filter(status=OrderDraft.STATUS_PENDING).order_by('-id').first()
    return ok({'reply': reply, 'draft': draft_to_dict(draft) if draft else None})


@require_http_methods(['GET'])
@api_login_required
def draft_detail(request, pk):
    customer = _current_customer(request)
    if customer is None:
        return fail('用户不存在', status=401)
    d = OrderDraft.objects.filter(id=pk, customer=customer).first()
    if not d:
        return fail('草稿不存在')
    return ok(draft_to_dict(d))


@require_http_methods(['POST'])
@api_login_required
def draft_confirm(request, pk):
    """顾客确认草稿：后端再次校验后生成正式订单。"""
    customer = _current_customer(request)
    if customer is None:
        return fail('用户不存在', status=401)
    d = OrderDraft.objects.filter(id=pk, customer=customer).first()
    if not d:
        return fail('草稿不存在')
    if d.status != OrderDraft.STATUS_PENDING:
        return fail('草稿状态不允许确认')

    delivery_fee = settings.DELIVERY_FEE

    with transaction.atomic():
        # 行锁内复核上架/数量/库存，全部通过后再扣减，防止确认瞬间超卖或负数量订单
        total = Decimal('0')
        resolved = []
        for it in d.items.all():
            p = ProductInfo.objects.select_for_update().filter(id=it.product_id).first()
            if p is None or p.status != 10:
                return fail(f'「{it.product.name}」已下架')
            if it.quantity <= 0:
                return fail(f'「{p.name}」数量非法')
            if p.stock < it.quantity:
                return fail(f'「{p.name}」库存不足')
            resolved.append((p, it.quantity))
        if not resolved:
            return fail('草稿内容为空')

        for p, qty in resolved:
            p.stock -= qty
            p.save(update_fields=['stock'])
            total += p.price * qty
        pay_amount = total + delivery_fee

        order = OrderInfo.objects.create(
            order_no=uuid.uuid4().hex[:20],
            user=d.customer,
            merchant=d.merchant,
            address_snapshot=(d.address.detail if d.address else ''),
            total_amount=total,
            delivery_fee=delivery_fee,
            pay_amount=pay_amount,
            status=OrderInfo.STATUS_PENDING_PAY,
            remark=d.remark or 'AI 点餐助手代下单',
        )
        for p, qty in resolved:
            OrderItem.objects.create(
                order=order, product=p, product_name=p.name,
                price=p.price, quantity=qty, amount=p.price * qty,
            )
        OrderStatusLog.objects.create(
            order=order, from_status=0, to_status=OrderInfo.STATUS_PENDING_PAY, operator_role='ai',
        )
        PaymentRecord.objects.create(order=order, amount=pay_amount, method='mock', status=10)

        d.status = OrderDraft.STATUS_CONFIRMED
        d.order = order
        d.confirm_time = timezone.now()
        d.save()

    return ok({'orderId': order.id, 'orderNo': order.order_no, 'actualAmount': float(pay_amount)})


@require_http_methods(['GET'])
@api_login_required
def recommend(request):
    """首页「猜你想吃」：口味画像 + 推荐菜品（无历史时返回冷启动结果）。"""
    customer = _current_customer(request)
    if customer is None:
        return fail('用户不存在', status=401)
    return ok({
        'profile': build_profile(customer),
        'dishes': recommend_dishes(customer),
    })


@require_http_methods(['POST'])
@api_login_required
def reorder(request):
    """一键复购：用最近一笔有效订单重建草稿（自动跳过下架/库存不足的菜）。"""
    customer = _current_customer(request)
    if customer is None:
        return fail('用户不存在', status=401)

    order, items, missing = build_reorder(customer)
    if order is None:
        return fail('还没有可复购的历史订单，先下一单试试')
    if not items:
        return fail('上次点的菜都不在售了，换个口味吧')

    address = customer.addresses.order_by('-is_default', '-id').first()
    total = sum((p.price * qty for p, qty in items), Decimal('0'))

    with transaction.atomic():
        draft = OrderDraft.objects.create(
            session=None, customer=customer, merchant=order.merchant,
            address=address, total_amount=total, status=OrderDraft.STATUS_PENDING,
        )
        for p, qty in items:
            OrderDraftItem.objects.create(
                draft=draft, product=p, quantity=qty, price_snapshot=p.price,
            )

    return ok({
        'draftId': draft.id,
        'merchantName': order.merchant.name,
        'sourceOrderNo': order.order_no,
        'total': float(total),
        'address': address.detail if address else '',
        'items': [{'name': p.name, 'quantity': q, 'price': float(p.price)} for p, q in items],
        'skipped': missing,
    }, info='已按上次订单生成草稿')
