from django.contrib import admin

from .models import OrderInfo, OrderItem, OrderStatusLog, UrgeRecord


@admin.register(OrderInfo)
class OrderInfoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order_no', 'user', 'merchant', 'pay_amount', 'status', 'rider', 'create_time',
    )
    list_filter = ('status', 'merchant')
    search_fields = ('order_no',)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product_name', 'spec_text', 'price', 'quantity', 'amount')
    search_fields = ('product_name',)


@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'from_status', 'to_status', 'operator_role', 'create_time')
    list_filter = ('operator_role',)


@admin.register(UrgeRecord)
class UrgeRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'operator_role', 'content', 'create_time')
    list_filter = ('operator_role',)
