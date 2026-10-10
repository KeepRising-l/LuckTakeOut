from django.db import models

from common.models import BaseModel


class Review(BaseModel):
    """评价（针对菜品或商户）"""

    TARGET_PRODUCT = 10
    TARGET_MERCHANT = 20

    TARGET_CHOICES = ((TARGET_PRODUCT, '菜品'), (TARGET_MERCHANT, '商户'))

    order = models.ForeignKey(
        'order.OrderInfo', on_delete=models.CASCADE,
        related_name='reviews', verbose_name='订单',
    )
    user = models.ForeignKey(
        'user.UserInfo', on_delete=models.CASCADE,
        related_name='reviews', verbose_name='评价人',
    )
    merchant = models.ForeignKey(
        'merchant.MerchantInfo', on_delete=models.CASCADE,
        related_name='reviews', verbose_name='被评商户',
    )
    product = models.ForeignKey(
        'product.ProductInfo', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviews', verbose_name='被评菜品',
    )
    target_type = models.SmallIntegerField('评价对象', choices=TARGET_CHOICES, default=TARGET_MERCHANT)
    rating = models.SmallIntegerField('评分', default=5, help_text='1-5')
    content = models.CharField('留言', max_length=255, blank=True, default='')

    class Meta:
        db_table = 'review'
        verbose_name = '评价'
        verbose_name_plural = verbose_name
