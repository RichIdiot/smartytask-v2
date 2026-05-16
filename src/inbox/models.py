"""Email-to-inbox handles and message log. See REBUILD_MODELS.md."""
import secrets
import uuid

from django.conf import settings
from django.db import models


def _gen_token() -> str:
    return secrets.token_urlsafe(24)


class InboxHandle(models.Model):
    """The email-to-inbox handle for a user.

    Postfix routes <handle>+<token>@inbox.smartytask.com → a Django webhook,
    which creates an InboxMessage and (usually) an Action. The +token requirement
    prevents the address from being a spam vector once it leaks.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="inbox_handle",
    )
    handle = models.SlugField(
        max_length=60, unique=True,
        help_text="The local part of the email-to-inbox address",
    )
    secret_token = models.CharField(
        max_length=40, default=_gen_token,
        help_text="Required as a +tag suffix to prevent spam",
    )
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inbox_handle"

    def __str__(self) -> str:
        return self.handle

    @property
    def address(self) -> str:
        from django.conf import settings as s
        return f"{self.handle}+{self.secret_token}@{s.INBOX_EMAIL_DOMAIN}"


class InboxMessage(models.Model):
    """Audit log of every email that hit the inbox endpoint."""

    class Disposition(models.TextChoices):
        CREATED_ACTION = "created", "Created an action"
        REJECTED_AUTH = "rejected_auth", "Rejected: bad token"
        REJECTED_QUOTA = "rejected_quota", "Rejected: over quota"
        ERROR = "error", "Error during processing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    handle = models.ForeignKey(
        InboxHandle, on_delete=models.CASCADE,
        related_name="messages", null=True, blank=True,
    )
    raw_from = models.CharField(max_length=320)
    subject = models.CharField(max_length=512, blank=True)
    body_text = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    disposition = models.CharField(max_length=24, choices=Disposition.choices)
    action = models.ForeignKey(
        "tasks.Action", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "inbox_message"
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.subject or '(no subject)'} from {self.raw_from}"
