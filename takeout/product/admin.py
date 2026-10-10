from django.contrib import admin

from .models import ProductCategory, ProductInfo, ProductSpec, ProductSku


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'merchant', 'sort')
    list_filter = ('merchant',)
    search_fields = ('name',)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'merchant', 'category', 'price', 'stock', 'status')
    list_filter = ('status', 'merchant')
    search_fields = ('name',)


@admin.register(ProductSpec)
class ProductSpecAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'name', 'options')
    search_fields = ('name',)


@admin.register(ProductSku)
class ProductSkuAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'spec_text', 'price', 'stock')
    search_fields = ('spec_text',)
