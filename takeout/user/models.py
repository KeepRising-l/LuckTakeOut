from django.conf import settings
from django.db import models

from common.models import BaseModel


class UserInfo(BaseModel):
    """顾客资料（登录账号复用 Django 内置 auth.User）"""

    GENDER_CHOICES = ((0, '未知'), (1, '男'), (2, '女'))

    auth_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='登录账号'
    )
    nickname = models.CharField('昵称', max_length=50)
    phone = models.CharField('手机号', max_length=20, unique=True)
    gender = models.SmallIntegerField('性别', choices=GENDER_CHOICES, default=0)
    avatar = models.CharField('头像', max_length=255, blank=True, default='')

    class Meta:
        db_table = 'user_info'
        verbose_name = '顾客资料'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.nickname


class UserAddress(BaseModel):
    """收货地址"""

    user = models.ForeignKey(
        UserInfo, on_delete=models.CASCADE, related_name='addresses', verbose_name='顾客'
    )
    receiver = models.CharField('收货人', max_length=50)
    phone = models.CharField('联系电话', max_length=20)
    province = models.CharField('省', max_length=50, blank=True, default='')
    city = models.CharField('市', max_length=50, blank=True, default='')
    district = models.CharField('区', max_length=50, blank=True, default='')
    detail = models.CharField('详细地址', max_length=200)
    is_default = models.BooleanField('是否默认', default=False)

    class Meta:
        db_table = 'user_address'
        verbose_name = '收货地址'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.receiver} {self.detail}'
