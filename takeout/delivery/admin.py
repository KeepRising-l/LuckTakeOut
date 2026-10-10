from django.contrib import admin

from .models import Rider


@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'status')
    list_filter = ('status',)
    search_fields = ('name', 'phone')
