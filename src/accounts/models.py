"""Custom User + per-user Preferences. See REBUILD_MODELS.md for design notes."""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Email-as-login user. UUID PK. Drop sha1 hashes from old app entirely."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    handle = models.CharField(
        max_length=30, unique=True, null=True, blank=True,
        help_text="Optional public handle; legacy username field",
    )
    first_name = models.CharField(max_length=60, blank=True)
    last_name = models.CharField(max_length=60, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "accounts_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_short_name(self) -> str:
        return self.first_name or self.email.split("@")[0]


class Preferences(models.Model):
    """Per-user app settings. 1:1 with User. Replaces legacy membership_profile."""

    class TicklerBehavior(models.IntegerChoices):
        OMIT = 0, "Omit from digest"
        TODAY_ONLY = 1, "Include today's ticklers only"
        TODAY_AND_OVERDUE = 2, "Include today's + overdue"
        ALL = 3, "Include all open ticklers"

    class ActionBehavior(models.IntegerChoices):
        OMIT = 0, "Omit from digest"
        STARRED_ONLY = 1, "Starred only"
        ALL_NEXT = 2, "All next actions"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")

    # Display preferences
    hide_empty_contexts = models.BooleanField(default=False)
    hide_empty_saved_views = models.BooleanField(default=False)
    saved_views_enabled = models.BooleanField(default=True)
    count_badges_on_contexts = models.BooleanField(default=True)
    count_badges_on_projects = models.BooleanField(default=True)
    use_stars = models.BooleanField(default=True)
    default_landing_page = models.CharField(
        max_length=40, default="inbox",
        help_text="View slug to land on after login",
    )

    # Time
    tz_name = models.CharField(
        max_length=64, default="UTC",
        help_text="IANA TZ string, e.g. America/Chicago",
    )

    # Reminder digest
    reminder_email = models.EmailField(
        blank=True, help_text="Override; falls back to user.email",
    )
    reminder_time = models.TimeField(default="08:00")
    reminder_tickler_behavior = models.IntegerField(
        choices=TicklerBehavior.choices, default=TicklerBehavior.TODAY_AND_OVERDUE,
    )
    reminder_action_behavior = models.IntegerField(
        choices=ActionBehavior.choices, default=ActionBehavior.STARRED_ONLY,
    )

    # Anything ad hoc lives here as JSON
    extra = models.JSONField(default=dict, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_preferences"
        verbose_name = "preferences"
        verbose_name_plural = "preferences"

    def __str__(self) -> str:
        return f"Preferences for {self.user.email}"
