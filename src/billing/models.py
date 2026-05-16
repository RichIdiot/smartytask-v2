"""Stripe-driven billing. See REBUILD_MODELS.md for design notes."""
import uuid

from django.conf import settings
from django.db import models


class Plan(models.Model):
    """A Stripe Price we sell. Synced from Stripe via management command."""

    class Interval(models.TextChoices):
        MONTH = "month", "Monthly"
        YEAR = "year", "Yearly"
        LIFETIME = "lifetime", "Lifetime (one-time)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stripe_price_id = models.CharField(max_length=64, unique=True)
    stripe_product_id = models.CharField(max_length=64)
    name = models.CharField(max_length=80)
    interval = models.CharField(max_length=16, choices=Interval.choices)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    is_active = models.BooleanField(default=True)
    is_founder_tier = models.BooleanField(
        default=False, help_text="First 500 lifetime founders",
    )

    class Meta:
        db_table = "billing_plan"

    def __str__(self) -> str:
        return self.name


class Subscription(models.Model):
    """A user's active subscription. 1:1 with User. Stripe is source of truth."""

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        INCOMPLETE = "incomplete", "Incomplete"
        LIFETIME = "lifetime", "Lifetime"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")

    stripe_customer_id = models.CharField(max_length=64, db_index=True)
    stripe_subscription_id = models.CharField(
        max_length=64, blank=True, db_index=True,
        help_text="Empty for lifetime/one-time",
    )

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.TRIALING,
    )
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_subscription"

    def __str__(self) -> str:
        return f"{self.user.email} — {self.plan.name} ({self.status})"

    @property
    def is_paid(self) -> bool:
        return self.status in {self.Status.ACTIVE, self.Status.TRIALING, self.Status.LIFETIME}


class StripeEvent(models.Model):
    """Idempotent webhook log. Process each Stripe event exactly once."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stripe_event_id = models.CharField(max_length=64, unique=True)
    event_type = models.CharField(max_length=80, db_index=True)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)

    class Meta:
        db_table = "billing_stripe_event"
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.event_type} ({self.stripe_event_id})"
