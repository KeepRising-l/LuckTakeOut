from django.db import models

from common.models import BaseModel


class PaymentRecord(BaseModel):
    """支付记录（模拟支付）"""

    STATUS_CHOICES = ((10, '待支付'), (20, '支付成功'), (30, '支付失败'))

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
    """退款记录（简化）"""

    STATUS_CHOICES = ((10, '申请中'), (20, '已退款'), (30, '已驳回'))

    order = models.ForeignKey(
        'order.OrderInfo', on_delete=models.CASCADE,
        related_name='refunds', verbose_name='订单',
    )
    user = models.ForeignKey(
        'user.UserInfo', on_delete=models.PROTECT,
        related_name='refunds', verbose_name='顾客',
    )
    amount = models.DecimalField('退款金额', max_digits=10, decimal_places=2)
    reason = models.CharField('退款原因', max_length=255, blank=True, default='')
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=10)
    finish_time = models.DateTimeField('完成时间', null=True, blank=True)

    class Meta:
        db_table = 'refund_record'
        verbose_name = '退款记录'
        verbose_name_plural = verbose_name
