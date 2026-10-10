from django.contrib import admin

from .models import UserInfo, UserAddress


@admin.register(UserInfo)
class UserInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nickname', 'phone', 'gender', 'create_time')
    search_fields = ('nickname', 'phone')
    list_filter = ('gender',)


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'receiver', 'phone', 'detail', 'is_default')
    search_fields = ('receiver', 'phone', 'detail')
    list_filter = ('is_default',)
