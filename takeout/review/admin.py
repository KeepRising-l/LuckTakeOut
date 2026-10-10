from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user', 'merchant', 'target_type', 'rating', 'create_time')
    list_filter = ('target_type', 'rating')
