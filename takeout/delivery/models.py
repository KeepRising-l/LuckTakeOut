from django.conf import settings
from django.db import models

from common.models import BaseModel


class Rider(BaseModel):
    """骑手（轻量配送）"""

    STATUS_CHOICES = ((0, '空闲'), (1, '忙碌'))

    auth_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='登录账号'
    )
    name = models.CharField('姓名', max_length=50)
    phone = models.CharField('手机号', max_length=20, blank=True, default='')
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=0)

    class Meta:
        db_table = 'rider'
        verbose_name = '骑手'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
