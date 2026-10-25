from django.db import models

from common.models import BaseModel


class PaymentRecord(BaseModel):
    """支付记录（模拟支付）"""

    STATUS_CHOICES = ((10, '待支付'), (20, '支付成功'), (30, '支付失败'), (40, '已退款'))

    order = models.ForeignKey(
        'order.OrderInfo', on_delete=models.CASCADE,
        related_name='payments', verbose_name='订单',
    )
    amount = models.DecimalField('金额', max_digits=10, decimal_places=2)
    method = models.CharField('支付方式', max_length=20, default='mock')
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=10)
    pay_time = models.DateTimeField('支付时间', null=True, blank=True)

    class Meta:
        db_table = 'payment_record'
        verbose_name = '支付记录'
        verbose_name_plural = verbose_name


class RefundRecord(BaseModel):
    """退款记录（模拟退款）：顾客申请 → 商户审核 → 模拟到账。

    from_status 记录申请时的订单状态，审核拒绝时按它把订单退回原状态。
    """

    STATUS_PENDING = 10
    STATUS_APPROVED = 20
    STATUS_REJECTED = 30
    STATUS_CHOICES = ((STATUS_PENDING, '待审核'), (STATUS_APPROVED, '已同意'), (STATUS_REJECTED, '已拒绝'))

    order = models.ForeignKey(
        'order.OrderInfo', on_delete=models.CASCADE,
        related_name='refunds', verbose_name='订单',
    )
    amount = models.DecimalField('退款金额', max_digits=10, decimal_places=2)
    reason = models.CharField('申请原因', max_length=255, blank=True, default='')
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=STATUS_PENDING)
    from_status = models.SmallIntegerField('申请时订单状态')
    review_remark = models.CharField('审核备注', max_length=255, blank=True, default='')
    review_time = models.DateTimeField('审核时间', null=True, blank=True)

    class Meta:
        db_table = 'refund_record'
        verbose_name = '退款记录'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.order_id}-{self.get_status_display()}'
