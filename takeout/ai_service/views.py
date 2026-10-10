"""AI 客服接口：会话、对话、草稿查看与确认。"""

import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from common.response import fail, ok
from common.utils import get_json
from order.models import OrderInfo, OrderItem, OrderStatusLog
from payment.models import PaymentRecord
from user.models import UserInfo

from .agent import run_agent
from .models import ChatSession, OrderDraft


def _default_customer():
    return UserInfo.objects.order_by('id').first()


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
                'spec': it.spec_text,
                'quantity': it.quantity,
                'price': float(it.price_snapshot),
            }
            for it in d.items.all()
        ],
    }


@require_http_methods(['POST'])
def create_session(request):
    data = get_json(request)
    customer = None
    if data.get('customerId'):
        customer = UserInfo.objects.filter(id=data['customerId']).first()
    customer = customer or _default_customer()
    if not customer:
        return fail('暂无顾客数据，请先执行 seed_demo')
    session = ChatSession.objects.create(customer=customer, status=10)
    return ok({
        'sessionId': session.id,
        'customerId': customer.id,
        'customerName': customer.nickname,
    })


@require_http_methods(['POST'])
def chat(request):
    data = get_json(request)
    message = (data.get('message') or '').strip()
    if not message:
        return fail('消息不能为空')
    session = ChatSession.objects.filter(id=data.get('sessionId')).first()
    if not session:
        return fail('会话不存在，请先创建会话')

    try:
        reply = run_agent(session, message)
    except Exception as e:  # noqa: BLE001
        return fail(f'AI 服务调用失败：{e}')
    draft = session.drafts.filter(status=OrderDraft.STATUS_PENDING).order_by('-id').first()
    return ok({'reply': reply, 'draft': draft_to_dict(draft) if draft else None})


@require_http_methods(['GET'])
def draft_detail(request, pk):
    d = OrderDraft.objects.filter(id=pk).first()
    if not d:
        return fail('草稿不存在')
    return ok(draft_to_dict(d))


@require_http_methods(['POST'])
def draft_confirm(request, pk):
    """顾客确认草稿：后端再次校验后生成正式订单。"""
    d = OrderDraft.objects.filter(id=pk).first()
    if not d:
        return fail('草稿不存在')
    if d.status != OrderDraft.STATUS_PENDING:
        return fail('草稿状态不允许确认')

    total = Decimal('0')
    resolved = []
    for it in d.items.all():
        p = it.product
        if p.status != 10:
            return fail(f'「{p.name}」已下架')
        if p.stock < it.quantity:
            return fail(f'「{p.name}」库存不足')
        amount = p.price * it.quantity
        total += amount
        resolved.append((p, it, amount))
    if not resolved:
        return fail('草稿内容为空')

    with transaction.atomic():
        order = OrderInfo.objects.create(
            order_no=uuid.uuid4().hex[:20],
            user=d.customer,
            merchant=d.merchant,
            address_snapshot=(d.address.detail if d.address else ''),
            total_amount=total,
            pay_amount=total,
            status=OrderInfo.STATUS_PENDING_PAY,
            remark='AI 客服代下单',
        )
        for p, it, amount in resolved:
            OrderItem.objects.create(
                order=order, product=p, sku=it.sku, product_name=p.name,
                spec_text=it.spec_text, price=p.price, quantity=it.quantity, amount=amount,
            )
        OrderStatusLog.objects.create(
            order=order, from_status=0, to_status=OrderInfo.STATUS_PENDING_PAY, operator_role='ai',
        )
        PaymentRecord.objects.create(order=order, amount=total, method='mock', status=10)

        d.status = OrderDraft.STATUS_CONFIRMED
        d.order = order
        d.confirm_time = timezone.now()
        d.save()

    return ok({'orderId': order.id, 'orderNo': order.order_no, 'actualAmount': float(total)})
