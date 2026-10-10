from django.contrib import admin

from .models import MerchantCategory, MerchantInfo


@admin.register(MerchantCategory)
class MerchantCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'sort')
    search_fields = ('name',)


@admin.register(MerchantInfo)
class MerchantInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'phone', 'status', 'create_time')
    list_filter = ('status', 'category')
    search_fields = ('name', 'phone')
