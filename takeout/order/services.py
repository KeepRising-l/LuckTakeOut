"""订单域跨视图复用的业务动作。"""

from django.db import transaction
from django.db.models import F

from payment.models import RefundRecord
from product.models import ProductInfo

from .models import OrderInfo
from .state import change_status


def restore_stock(order):
    """取消订单时按明细回补库存（须在事务内调用）。"""
    for it in order.items.all():
        ProductInfo.objects.filter(id=it.product_id).update(stock=F('stock') + it.quantity)


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
