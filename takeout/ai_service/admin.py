from django.contrib import admin

from .models import ChatMessage, ChatSession, OrderDraft, OrderDraftItem


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'cs_user', 'status', 'create_time')
    list_filter = ('status',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'tool_name', 'content', 'create_time')
    list_filter = ('role',)


@admin.register(OrderDraft)
class OrderDraftAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'merchant', 'total_amount', 'status', 'order', 'create_time')
    list_filter = ('status',)


@admin.register(OrderDraftItem)
class OrderDraftItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'draft', 'product', 'spec_text', 'quantity', 'price_snapshot')
