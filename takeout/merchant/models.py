from django.conf import settings
from django.db import models

from common.models import BaseModel


class MerchantCategory(BaseModel):
    """商户分类"""

    name = models.CharField('分类名称', max_length=50)
    sort = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'merchant_category'
        verbose_name = '商户分类'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class MerchantInfo(BaseModel):
    """商户"""

    STATUS_PENDING = 10
    STATUS_APPROVED = 20
    STATUS_REJECTED = 30
    STATUS_CHOICES = (
        (STATUS_PENDING, '待审核'),
        (STATUS_APPROVED, '已通过'),
        (STATUS_REJECTED, '已驳回'),
    )

    auth_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='登录账号'
    )
    name = models.CharField('商户名称', max_length=100)
    category = models.ForeignKey(
        MerchantCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='merchants', verbose_name='商户分类',
    )
    logo = models.CharField('门店图片', max_length=255, blank=True, default='')
    phone = models.CharField('联系电话', max_length=20, blank=True, default='')
    address = models.CharField('商户地址', max_length=200, blank=True, default='')
    description = models.CharField('简介', max_length=255, blank=True, default='')
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=STATUS_PENDING)
    is_open = models.BooleanField('营业中', default=True)
    open_time = models.TimeField('开始营业', null=True, blank=True)
    close_time = models.TimeField('结束营业', null=True, blank=True)

    class Meta:
        db_table = 'merchant_info'
        verbose_name = '商户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
