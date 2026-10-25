"""订单状态机：合法迁移表与统一的状态变更入口。

所有订单状态变更都应经过 `change_status`，由它校验迁移合法性、落库并写入状态日志。
非法迁移一律被拒绝，返回 False。
"""

from django.db import transaction

from .models import OrderInfo, OrderStatusLog

ALLOWED_TRANSITIONS = {
    OrderInfo.STATUS_PENDING_PAY: {OrderInfo.STATUS_PAID, OrderInfo.STATUS_CANCELED},
    OrderInfo.STATUS_PAID: {
        OrderInfo.STATUS_PENDING_ACCEPT, OrderInfo.STATUS_CANCELED, OrderInfo.STATUS_REFUNDING,
    },
    OrderInfo.STATUS_PENDING_ACCEPT: {
        OrderInfo.STATUS_DELIVERING, OrderInfo.STATUS_CANCELED, OrderInfo.STATUS_REFUNDING,
    },
    # 退款中：审核通过 → 已退款；审核拒绝 → 退回申请前状态（PAID / PENDING_ACCEPT）
    OrderInfo.STATUS_REFUNDING: {
        OrderInfo.STATUS_REFUNDED, OrderInfo.STATUS_PAID, OrderInfo.STATUS_PENDING_ACCEPT,
    },
    OrderInfo.STATUS_DELIVERING: {OrderInfo.STATUS_FINISHED},
    OrderInfo.STATUS_FINISHED: set(),
    OrderInfo.STATUS_CANCELED: set(),
    OrderInfo.STATUS_REFUNDED: set(),
}

# 商户端可提交的目标状态（对外契约的一部分）
MERCHANT_TARGET_STATUSES = {
    OrderInfo.STATUS_PENDING_ACCEPT,
    OrderInfo.STATUS_FINISHED,
    OrderInfo.STATUS_CANCELED,
}


def can_transition(from_status, to_status):
    """判断状态迁移是否合法。"""
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())


def change_status(order, to_status, operator_role, operator_id=None, **fields):
    """执行一次状态变更。

    返回 (是否成功, 提示信息)。状态未变化视为成功且不写日志；
    非法迁移不落库、不写日志。
    """
    if order.status == to_status:
        return True, ''

    if not can_transition(order.status, to_status):
        return False, '当前订单状态不允许该操作'

    from_status = order.status
    order.status = to_status
    for name, value in fields.items():
        setattr(order, name, value)
    # 状态落库与日志同事务，避免中途失败导致状态与日志不一致
    with transaction.atomic():
        order.save()

        OrderStatusLog.objects.create(
            order=order, from_status=from_status, to_status=to_status,
            operator_id=operator_id, operator_role=operator_role,
        )
    return True, ''
