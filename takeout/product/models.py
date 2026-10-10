from django.db import models

from common.models import BaseModel


class ProductCategory(BaseModel):
    """菜品分类"""

    merchant = models.ForeignKey(
        'merchant.MerchantInfo', on_delete=models.CASCADE,
        related_name='categories', verbose_name='所属商户',
    )
    name = models.CharField('分类名称', max_length=50)
    sort = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'product_category'
        verbose_name = '菜品分类'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ProductInfo(BaseModel):
    """菜品"""

    STATUS_CHOICES = ((10, '上架'), (20, '下架'))

    merchant = models.ForeignKey(
        'merchant.MerchantInfo', on_delete=models.CASCADE,
        related_name='products', verbose_name='所属商户',
    )
    category = models.ForeignKey(
        ProductCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='products', verbose_name='分类',
    )
    name = models.CharField('菜品名称', max_length=100)
    image = models.CharField('图片', max_length=255, blank=True, default='')
    description = models.CharField('描述', max_length=255, blank=True, default='')
    price = models.DecimalField('价格', max_digits=10, decimal_places=2, default=0)
    stock = models.IntegerField('库存', default=0)
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=10)

    class Meta:
        db_table = 'product_info'
        verbose_name = '菜品'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ProductSpec(BaseModel):
    """规格项（如：辣度）"""

    product = models.ForeignKey(
        ProductInfo, on_delete=models.CASCADE, related_name='specs', verbose_name='菜品'
    )
    name = models.CharField('规格名', max_length=50)
    options = models.CharField('可选值', max_length=255, help_text='逗号分隔，如：微辣,中辣,特辣')

    class Meta:
        db_table = 'product_spec'
        verbose_name = '菜品规格项'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.product.name}-{self.name}'


class ProductSku(BaseModel):
    """规格组合 / 可售单元（含价格与库存）"""

    product = models.ForeignKey(
        ProductInfo, on_delete=models.CASCADE, related_name='skus', verbose_name='菜品'
    )
    spec_text = models.CharField('规格描述', max_length=100, blank=True, default='')
    price = models.DecimalField('价格', max_digits=10, decimal_places=2, default=0)
    stock = models.IntegerField('库存', default=0)

    class Meta:
        db_table = 'product_sku'
        verbose_name = '菜品SKU'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.product.name}-{self.spec_text}'
