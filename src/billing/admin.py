from django.contrib import admin

from .models import Plan, StripeEvent, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "interval", "amount_cents", "currency", "is_active", "is_founder_tier")
    list_filter = ("interval", "is_active", "is_founder_tier")
    search_fields = ("name", "stripe_price_id")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "current_period_end", "cancel_at_period_end")
    list_filter = ("status",)
    search_fields = ("user__email", "stripe_customer_id", "stripe_subscription_id")
    raw_id_fields = ("user", "plan")


@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = ("stripe_event_id", "event_type", "received_at", "processed_at")
    list_filter = ("event_type",)
    search_fields = ("stripe_event_id", "event_type")
    readonly_fields = ("received_at",)
