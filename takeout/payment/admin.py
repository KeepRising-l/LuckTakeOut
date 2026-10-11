from django.contrib import admin

from .models import PaymentRecord


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'amount', 'method', 'status', 'pay_time')
    list_filter = ('status', 'method')
