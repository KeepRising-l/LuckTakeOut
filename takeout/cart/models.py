from django.db import models

from common.models import BaseModel


class ShoppingCart(BaseModel):
    """购物车"""

    user = models.ForeignKey(
        'user.UserInfo', on_delete=models.CASCADE,
        related_name='cart_items', verbose_name='顾客',
    )
    merchant = models.ForeignKey(
        'merchant.MerchantInfo', on_delete=models.CASCADE,
        related_name='cart_items', verbose_name='商户',
    )
    product = models.ForeignKey(
        'product.ProductInfo', on_delete=models.CASCADE,
        related_name='cart_items', verbose_name='菜品',
    )
    sku = models.ForeignKey(
        'product.ProductSku', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cart_items', verbose_name='规格',
    )
    quantity = models.IntegerField('数量', default=1)

    class Meta:
        db_table = 'shopping_cart'
        verbose_name = '购物车'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.user} - {self.product} x{self.quantity}'
