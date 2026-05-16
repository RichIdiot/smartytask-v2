from django.contrib import admin

from .models import InboxHandle, InboxMessage


@admin.register(InboxHandle)
class InboxHandleAdmin(admin.ModelAdmin):
    list_display = ("handle", "user", "is_active", "created")
    list_filter = ("is_active",)
    search_fields = ("handle", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = ("secret_token",)


@admin.register(InboxMessage)
class InboxMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "raw_from", "handle", "disposition", "received_at")
    list_filter = ("disposition",)
    search_fields = ("subject", "raw_from", "body_text")
    raw_id_fields = ("handle", "action")
    readonly_fields = ("received_at",)
