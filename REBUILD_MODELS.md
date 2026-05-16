# SmartyTask v2 Model Architecture

Derived from `REBUILD_SPEC.md`. This document defines the Django 5 model code that the scaffold will install. Treat it as the contract between the spec and the implementation.

---

## App split

Four Django apps, each owning a clear domain:

| App | Owns | Notes |
|---|---|---|
| `accounts` | `User`, `Preferences` | Custom User from day one. Email = login. Argon2 hashing. |
| `tasks` | `Context`, `Project`, `Action`, `SomedayList`, `Altitude`, `SavedView`, `SavedViewRule` | The GTD core. Where 99% of product logic lives. |
| `inbox` | `InboxHandle`, `InboxMessage` | Email-to-inbox. Postfix → webhook → Action. |
| `billing` | `Plan`, `Subscription`, `StripeEvent` | Stripe-driven. Webhooks land in `StripeEvent`, processor mutates `Subscription`. |

---

## `accounts` app

```python
# accounts/models.py
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    handle = models.CharField(max_length=30, unique=True, null=True, blank=True,
                              help_text="Optional public handle; legacy username field")
    first_name = models.CharField(max_length=60, blank=True)
    last_name = models.CharField(max_length=60, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "accounts_user"

    def __str__(self) -> str:
        return self.email


class Preferences(models.Model):
    """Per-user app settings. 1:1 with User. Replaces old membership_profile."""

    class TicklerBehavior(models.IntegerChoices):
        OMIT = 0, "Omit from digest"
        TODAY_ONLY = 1, "Include today's ticklers only"
        TODAY_AND_OVERDUE = 2, "Include today's + overdue"
        ALL = 3, "Include all open ticklers"

    class ActionBehavior(models.IntegerChoices):
        OMIT = 0, "Omit from digest"
        STARRED_ONLY = 1, "Starred only"
        ALL_NEXT = 2, "All next actions"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")

    # Display preferences
    hide_empty_contexts = models.BooleanField(default=False)
    hide_empty_saved_views = models.BooleanField(default=False)
    saved_views_enabled = models.BooleanField(default=True)
    count_badges_on_contexts = models.BooleanField(default=True)
    count_badges_on_projects = models.BooleanField(default=True)
    use_stars = models.BooleanField(default=True)
    default_landing_page = models.CharField(max_length=40, default="inbox",
                                            help_text="View slug to land on after login")

    # Time
    timezone = models.CharField(max_length=64, default="UTC",
                                help_text="IANA TZ string, e.g. America/Chicago")

    # Reminder digest
    reminder_email = models.EmailField(blank=True,
                                       help_text="Override; falls back to user.email")
    reminder_time = models.TimeField(default="08:00")
    reminder_tickler_behavior = models.IntegerField(choices=TicklerBehavior.choices,
                                                    default=TicklerBehavior.TODAY_AND_OVERDUE)
    reminder_action_behavior = models.IntegerField(choices=ActionBehavior.choices,
                                                   default=ActionBehavior.STARRED_ONLY)

    # Anything ad hoc
    extra = models.JSONField(default=dict, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_preferences"

    def __str__(self) -> str:
        return f"Preferences for {self.user.email}"
```

---

## `tasks` app

```python
# tasks/models.py
import uuid
from django.conf import settings
from django.db import models
from treebeard.mp_tree import MP_Node


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def active(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)


class Context(TimeStampedModel):
    """GTD context (@home, @phone, @errands). One level of nesting allowed."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="contexts", db_index=True)
    title = models.CharField(max_length=120)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True,
                               related_name="children", db_index=True)
    is_active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "tasks_context"
        ordering = ["position", "title"]

    def __str__(self) -> str:
        return self.title


class Project(TimeStampedModel):
    """A multi-step outcome. Has actions belonging to it."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="projects", db_index=True)
    title = models.CharField(max_length=256)
    notes = models.TextField(blank=True, help_text="Markdown")
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_collapsed = models.BooleanField(default=False, help_text="UI state in list view")
    position = models.PositiveIntegerField(default=0)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        db_table = "tasks_project"
        ordering = ["position", "-created"]

    def __str__(self) -> str:
        return self.title


class SomedayList(TimeStampedModel):
    """Bucket for someday/maybe items. Was smarty_somedaycategory."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="someday_lists", db_index=True)
    title = models.CharField(max_length=120)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "tasks_someday_list"
        ordering = ["position", "title"]

    def __str__(self) -> str:
        return self.title


class Altitude(MP_Node):
    """David Allen's altitude hierarchy. Full 5-level horizon model.

    Allen's levels (from ground up):
      - Ground (Runway): current actions
      - 10K ft: current projects
      - 20K ft: areas of focus and responsibility
      - 30K ft: 1-2 year goals
      - 40K ft: 3-5 year vision
      - 50K ft: life purpose

    The model supports arbitrary depth; the default seed populates Allen's six.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="altitudes", db_index=True)
    title = models.CharField(max_length=2000)
    is_collapsed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    node_order_by = ["title"]

    class Meta:
        db_table = "tasks_altitude"

    def __str__(self) -> str:
        return self.title[:80]


class Action(TimeStampedModel):
    """An action / task / tickler. The load-bearing table."""

    class Status(models.TextChoices):
        INBOX = "inbox", "Inbox"
        NEXT = "next", "Next action"
        SCHEDULED = "scheduled", "Scheduled"
        WAITING = "waiting", "Waiting on"
        SOMEDAY = "someday", "Someday/maybe"
        TICKLER = "tickler", "Tickler"
        COMPLETED = "completed", "Completed"

    class Effort(models.IntegerChoices):
        LOW = 1, "Low"
        MEDIUM = 2, "Medium"
        HIGH = 3, "High"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="actions", db_index=True)
    context = models.ForeignKey(Context, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="actions", db_index=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="actions", db_index=True)
    someday_list = models.ForeignKey(SomedayList, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="actions",
                                     db_index=True)

    title = models.CharField(max_length=256)
    notes = models.TextField(blank=True, help_text="Markdown")

    status = models.CharField(max_length=16, choices=Status.choices,
                              default=Status.INBOX, db_index=True)
    starred = models.BooleanField(default=False, db_index=True)

    effort = models.IntegerField(choices=Effort.choices, null=True, blank=True)
    minutes_required = models.PositiveIntegerField(null=True, blank=True)

    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_reminded_at = models.DateTimeField(null=True, blank=True)

    position = models.IntegerField(default=0,
                                   help_text="Manual reorder within current view")

    extra = models.JSONField(default=dict, blank=True)

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        db_table = "tasks_action"
        ordering = ["position", "-created"]
        indexes = [
            # The killer composite from the old schema, modernized
            models.Index(fields=["user", "deleted_at", "completed_at", "status"],
                         name="i_user_del_comp_status"),
            models.Index(fields=["user", "due_date"], name="i_user_due"),
        ]

    def __str__(self) -> str:
        return self.title[:80]


class SavedView(TimeStampedModel):
    """A saved query over actions. Was smarty_smartcontext.

    Renamed for clarity — "smart context" was confusing terminology that
    overloaded the meaning of "context" in GTD.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="saved_views", db_index=True)
    title = models.CharField(max_length=120)
    feed_slug = models.SlugField(max_length=50, null=True, blank=True,
                                 help_text="Public RSS/iCal feed slug")
    position = models.PositiveIntegerField(default=0)

    # JSON DSL for the filter — replaces smarty_smartcontextrule + _contexts entirely.
    # Example: {
    #   "effort_in": [1, 2],
    #   "starred": true,
    #   "context_in": ["uuid-1", "uuid-2"],
    #   "use_context_filter": true,
    #   "created_within_days": 30,
    #   "due_within_days": 7
    # }
    rule = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "tasks_saved_view"
        ordering = ["position", "title"]

    def __str__(self) -> str:
        return self.title
```

The old `smarty_smartcontextrule` and `smarty_smartcontextrule_contexts` collapse into one `rule` JSONField on `SavedView`. A single evaluator function lives in `tasks/saved_views.py` that takes a rule dict and an Action queryset and returns the filtered queryset. Much less code than the old 14-field rule table.

---

## `inbox` app

```python
# inbox/models.py
import uuid
from django.conf import settings
from django.db import models


class InboxHandle(models.Model):
    """The email-to-inbox handle for a user.

    Postfix routes <handle>@inbox.smartytask.com → a Django webhook,
    which creates an InboxMessage and (usually) an Action.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="inbox_handle")
    handle = models.SlugField(max_length=60, unique=True,
                              help_text="The local part of the email-to-inbox address")
    secret_token = models.CharField(max_length=40,
                                    help_text="Required as a +tag suffix to prevent spam")
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inbox_handle"

    @property
    def address(self) -> str:
        return f"{self.handle}+{self.secret_token}@inbox.smartytask.com"


class InboxMessage(models.Model):
    """Audit log of every email that hit the inbox endpoint."""

    class Disposition(models.TextChoices):
        CREATED_ACTION = "created", "Created an action"
        REJECTED_AUTH = "rejected_auth", "Rejected: bad token"
        REJECTED_QUOTA = "rejected_quota", "Rejected: over quota"
        ERROR = "error", "Error during processing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    handle = models.ForeignKey(InboxHandle, on_delete=models.CASCADE,
                               related_name="messages", null=True, blank=True)
    raw_from = models.CharField(max_length=320)
    subject = models.CharField(max_length=512, blank=True)
    body_text = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    disposition = models.CharField(max_length=24, choices=Disposition.choices)
    action = models.ForeignKey("tasks.Action", on_delete=models.SET_NULL,
                               null=True, blank=True, related_name="+")
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "inbox_message"
        ordering = ["-received_at"]
```

Key design choice: the `secret_token` requirement (as a `+tag` after the handle) prevents the email-to-inbox feature from becoming a spam vector the moment a handle leaks. Postfix forwards everything to `*@inbox.smartytask.com`; the webhook validates the token and rejects unknown senders.

---

## `billing` app

```python
# billing/models.py
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
    is_founder_tier = models.BooleanField(default=False,
                                          help_text="First 500 lifetime founders")

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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")

    stripe_customer_id = models.CharField(max_length=64, db_index=True)
    stripe_subscription_id = models.CharField(max_length=64, blank=True, db_index=True,
                                              help_text="Empty for lifetime/one-time")

    status = models.CharField(max_length=16, choices=Status.choices,
                              default=Status.TRIALING)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_subscription"

    @property
    def is_paid(self) -> bool:
        return self.status in {self.Status.ACTIVE, self.Status.TRIALING,
                               self.Status.LIFETIME}


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
```

---

## Key modernization decisions, summarized

1. **UUID primary keys** across the board. No more leaking row counts via sequential integer IDs.
2. **Email = login.** Username drops to optional `handle`.
3. **Argon2** for password hashing.
4. **Single `status` enum on Action** replaces the (`deleted`, `completed`, `is_tickler`, plus implied state) combinatorial nightmare.
5. **One `position` field, not four** ordering columns.
6. **JSONField for `extra`/`rule`** instead of single-quoted text blobs.
7. **`treebeard` instead of `mptt`** for Altitude (active maintenance).
8. **Markdown notes** instead of HTML rich text.
9. **Saved view rules collapse** from a 14-field model + M2M into a single JSON DSL evaluated server-side.
10. **Soft delete via `deleted_at`** stays — preserves the old "trash can" UX.
11. **Stripe webhooks land in `StripeEvent`** first, then a processor mutates state. Idempotent and replayable.

---

## Next deliverable

The scaffolded project (Task #14) will install these models verbatim. After scaffold + `manage.py makemigrations` + `manage.py migrate`, we'll have a working empty database with this exact schema and zero legacy code.
