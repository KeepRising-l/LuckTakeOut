from django.db import models

from common.models import BaseModel


class ChatSession(BaseModel):
    """AI 点餐助手会话（作用域为发起会话的顾客）"""

    STATUS_CHOICES = ((10, '进行中'), (20, '已结束'))

    customer = models.ForeignKey(
        'user.UserInfo', on_delete=models.CASCADE,
        related_name='chat_sessions', verbose_name='顾客',
    )
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=10)

    class Meta:
        db_table = 'chat_session'
        verbose_name = '客服会话'
        verbose_name_plural = verbose_name


class ChatMessage(BaseModel):
    """会话消息"""

    ROLE_CHOICES = (
        ('user', '用户'),
        ('assistant', '助手'),
        ('system', '系统'),
        ('tool', '工具'),
    )

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE,
        related_name='messages', verbose_name='会话',
    )
    role = models.CharField('角色', max_length=20, choices=ROLE_CHOICES)
    content = models.TextField('内容', blank=True, default='')
    tool_name = models.CharField('工具名', max_length=50, blank=True, default='')

    class Meta:
        db_table = 'chat_message'
        verbose_name = '会话消息'
        verbose_name_plural = verbose_name


class OrderDraft(BaseModel):
    """订单草稿（AI 生成，待顾客确认，不产生真实交易）"""

    STATUS_PENDING = 10
    STATUS_CONFIRMED = 20
    STATUS_VOID = 30

    STATUS_CHOICES = (
        (STATUS_PENDING, '待确认'),
        (STATUS_CONFIRMED, '已确认'),
        (STATUS_VOID, '已作废'),
    )

    session = models.ForeignKey(
        ChatSession, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='drafts', verbose_name='所属会话',
    )
    customer = models.ForeignKey(
        'user.UserInfo', on_delete=models.CASCADE,
        related_name='drafts', verbose_name='顾客',
    )
    merchant = models.ForeignKey(
        'merchant.MerchantInfo', on_delete=models.PROTECT,
        related_name='drafts', verbose_name='商户',
    )
    address = models.ForeignKey(
        'user.UserAddress', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='drafts', verbose_name='收货地址',
    )
    total_amount = models.DecimalField('草稿金额', max_digits=10, decimal_places=2, default=0)
    remark = models.CharField('订单备注', max_length=255, blank=True, default='')
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=STATUS_PENDING)
    order = models.OneToOneField(
        'order.OrderInfo', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='draft', verbose_name='正式订单',
    )
    confirm_time = models.DateTimeField('确认时间', null=True, blank=True)

    class Meta:
        db_table = 'order_draft'
        verbose_name = '订单草稿'
        verbose_name_plural = verbose_name


class OrderDraftItem(BaseModel):
    """订单草稿明细"""

    draft = models.ForeignKey(
        OrderDraft, on_delete=models.CASCADE,
        related_name='items', verbose_name='草稿',
    )
    product = models.ForeignKey(
        'product.ProductInfo', on_delete=models.PROTECT,
        related_name='draft_items', verbose_name='菜品',
    )
    quantity = models.IntegerField('数量', default=1)
    price_snapshot = models.DecimalField('单价快照', max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_draft_item'
        verbose_name = '订单草稿明细'
        verbose_name_plural = verbose_name
