from django.contrib import admin

from .models import Notification, OperationLog, SystemConfig

admin.site.site_header = '外卖平台 · 运营后台'
admin.site.site_title = '外卖平台运营后台'
admin.site.index_title = '平台管理'


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'actor_id', 'actor_role', 'action', 'target_type', 'target_id', 'result', 'create_time',
    )
    list_filter = ('actor_role', 'action')
    search_fields = ('action', 'target_type')
    readonly_fields = ('create_time',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'to_user', 'title', 'type', 'is_read', 'create_time')
    list_filter = ('type', 'is_read')
    search_fields = ('title',)


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'config_key', 'config_value', 'remark')
    search_fields = ('config_key',)
