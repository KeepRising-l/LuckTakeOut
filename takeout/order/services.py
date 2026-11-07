"""订单域跨视图复用的业务动作。"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from payment.models import RefundRecord
from platform_ops.models import Notification
from product.models import ProductInfo

from .models import OrderInfo
from .state import change_status


def restore_stock(order):
    """取消订单时按明细回补库存（须在事务内调用）。"""
    for it in order.items.all():
        ProductInfo.objects.filter(id=it.product_id).update(stock=F('stock') + it.quantity)


def notify_merchant_new_order(order):
    """支付成功后给商家写一条「新订单」站内信（须与支付状态变更同事务调用）。"""
    Notification.objects.create(
        to_user=order.merchant.auth_user,
        title='新订单待接单',
        content=(
            f'订单 {order.order_no}，实付 {order.pay_amount} 元，'
            '请尽快进入订单管理接单'
        ),
        type=Notification.TYPE_NEW_ORDER,
    )


def cancel_expired_unpaid_orders(timeout_minutes=None, now=None):
    """取消超过时限仍未支付的订单并回补库存，返回实际取消数量。

    - 默认超时分钟数取 settings.UNPAID_ORDER_TIMEOUT_MINUTES；
    - 逐单加行锁后二次校验状态与时间，重复执行不会重复取消或重复回补；
    - 已支付/已取消的订单不会被处理。
    """
    if timeout_minutes is None:
        timeout_minutes = getattr(settings, 'UNPAID_ORDER_TIMEOUT_MINUTES', 15)
    timeout_minutes = int(timeout_minutes)
    if timeout_minutes <= 0:
        raise ValueError('超时分钟数必须为正整数')

    now = now or timezone.now()
    cutoff = now - timedelta(minutes=timeout_minutes)
    order_ids = list(
        OrderInfo.objects.filter(
            status=OrderInfo.STATUS_PENDING_PAY,
            create_time__lt=cutoff,
        ).values_list('id', flat=True)
    )

    canceled = 0
    for order_id in order_ids:
        with transaction.atomic():
            order = OrderInfo.objects.select_for_update().filter(id=order_id).first()
            # 行锁后重新校验：期间可能已被支付或人工取消
            if not order or order.status != OrderInfo.STATUS_PENDING_PAY:
                continue
            if order.create_time >= cutoff:
                continue
            changed, _ = change_status(
                order, OrderInfo.STATUS_CANCELED, operator_role='system',
            )
            if not changed:
                continue
            restore_stock(order)
            canceled += 1
    return canceled


def apply_refund_for_order(order_id, user_info, reason='', operator_role='customer'):
    """顾客申请退款：已支付/待接单订单进入「退款中」并生成待审核退款记录。

    HTTP 视图与 AI 工具共用同一套状态校验；返回 (是否成功, 提示信息, RefundRecord|None)。
    """
    with transaction.atomic():
        o = OrderInfo.objects.select_for_update().filter(id=order_id, user=user_info).first()
        if not o:
            return False, '订单不存在', None
        if o.refunds.filter(status=RefundRecord.STATUS_PENDING).exists():
            return False, '已有退款申请待审核，请耐心等待', None
        if o.status not in (OrderInfo.STATUS_PAID, OrderInfo.STATUS_PENDING_ACCEPT):
            return False, '当前订单状态不支持申请退款', None

        from_status = o.status
        changed, message = change_status(
            o, OrderInfo.STATUS_REFUNDING, operator_role=operator_role, operator_id=user_info.id,
        )
        if not changed:
            return False, message, None
        refund = RefundRecord.objects.create(
            order=o,
            amount=o.pay_amount,
            reason=(reason or '').strip()[:255],
            status=RefundRecord.STATUS_PENDING,
            from_status=from_status,
        )
    return True, '退款申请已提交，等待商家审核', refund
