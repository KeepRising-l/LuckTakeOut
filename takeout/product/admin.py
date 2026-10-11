from django.contrib import admin

from .models import ProductCategory, ProductInfo


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
