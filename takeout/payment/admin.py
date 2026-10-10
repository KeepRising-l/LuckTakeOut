from django.contrib import admin

from .models import PaymentRecord, RefundRecord


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'amount', 'method', 'status', 'pay_time')
    list_filter = ('status', 'method')


@admin.register(RefundRecord)
class RefundRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user', 'amount', 'status', 'create_time')
    list_filter = ('status',)
