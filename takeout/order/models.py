from django.db import models

from common.models import BaseModel


class OrderInfo(BaseModel):
    """订单主表（一个订单仅属于一个商户）"""

    STATUS_PENDING_PAY = 10
    STATUS_PAID = 20
    STATUS_PENDING_ACCEPT = 30
    STATUS_DELIVERING = 40
    STATUS_FINISHED = 50
    STATUS_CANCELED = 60
    STATUS_REFUNDING = 70
    STATUS_REFUNDED = 80

    STATUS_CHOICES = (
        (STATUS_PENDING_PAY, '待支付'),
        (STATUS_PAID, '已支付'),
        (STATUS_PENDING_ACCEPT, '待接单'),
        (STATUS_DELIVERING, '配送中'),
        (STATUS_FINISHED, '已完成'),
        (STATUS_CANCELED, '已取消'),
        (STATUS_REFUNDING, '退款中'),
        (STATUS_REFUNDED, '已退款'),
    )

    order_no = models.CharField('订单号', max_length=32, unique=True)
    user = models.ForeignKey(
        'user.UserInfo', on_delete=models.PROTECT,
        related_name='orders', verbose_name='顾客',
    )
    merchant = models.ForeignKey(
        'merchant.MerchantInfo', on_delete=models.PROTECT,
        related_name='orders', verbose_name='商户',
    )
    address_snapshot = models.CharField('收货地址快照', max_length=300)
    total_amount = models.DecimalField('商品总额', max_digits=10, decimal_places=2, default=0)
    pay_amount = models.DecimalField('实付金额', max_digits=10, decimal_places=2, default=0)
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=STATUS_PENDING_PAY)
    rider = models.ForeignKey(
        'delivery.Rider', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders', verbose_name='骑手',
    )
    remark = models.CharField('备注', max_length=255, blank=True, default='')
    pay_time = models.DateTimeField('支付时间', null=True, blank=True)
    deliver_time = models.DateTimeField('送达时间', null=True, blank=True)
    finish_time = models.DateTimeField('完成时间', null=True, blank=True)

    class Meta:
        db_table = 'order_info'
        verbose_name = '订单'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['merchant', 'status']),
        ]

    def __str__(self):
        return self.order_no


class OrderItem(BaseModel):
    """订单明细（含商品快照）"""

    order = models.ForeignKey(
        OrderInfo, on_delete=models.CASCADE, related_name='items', verbose_name='订单'
    )
    product = models.ForeignKey(
        'product.ProductInfo', on_delete=models.PROTECT,
        related_name='order_items', verbose_name='菜品',
    )
    sku = models.ForeignKey(
        'product.ProductSku', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='order_items', verbose_name='规格',
    )
    product_name = models.CharField('菜品名称快照', max_length=100)
    spec_text = models.CharField('规格快照', max_length=100, blank=True, default='')
    price = models.DecimalField('单价快照', max_digits=10, decimal_places=2)
    quantity = models.IntegerField('数量', default=1)
    amount = models.DecimalField('小计', max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_item'
        verbose_name = '订单明细'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.order_id}-{self.product_name}'


class OrderStatusLog(BaseModel):
    """订单状态变更日志"""

    order = models.ForeignKey(
        OrderInfo, on_delete=models.CASCADE, related_name='status_logs', verbose_name='订单'
    )
    from_status = models.SmallIntegerField('原状态')
    to_status = models.SmallIntegerField('新状态')
    operator_id = models.IntegerField('操作者ID', null=True, blank=True)
    operator_role = models.CharField('操作者角色', max_length=20, blank=True, default='')

    class Meta:
        db_table = 'order_status_log'
        verbose_name = '订单状态日志'
        verbose_name_plural = verbose_name


class UrgeRecord(BaseModel):
    """催单记录"""

    order = models.ForeignKey(
        OrderInfo, on_delete=models.CASCADE, related_name='urges', verbose_name='订单'
    )
    operator_id = models.IntegerField('操作者ID', null=True, blank=True)
    operator_role = models.CharField('操作者角色', max_length=20, blank=True, default='')
    content = models.CharField('催单内容', max_length=255, blank=True, default='')

    class Meta:
        db_table = 'urge_record'
        verbose_name = '催单记录'
        verbose_name_plural = verbose_name
