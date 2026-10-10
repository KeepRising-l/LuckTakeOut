from django.contrib import admin

from .models import ShoppingCart


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'merchant', 'product', 'sku', 'quantity', 'create_time')
    list_filter = ('merchant',)
    search_fields = ('user__nickname', 'product__name')
