"""GTD core models. See REBUILD_MODELS.md for design notes."""
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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="contexts", db_index=True,
    )
    title = models.CharField(max_length=120)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children", db_index=True,
    )
    is_active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "tasks_context"
        ordering = ["position", "title"]

    def __str__(self) -> str:
        return self.title


class Project(TimeStampedModel):
    """A multi-step outcome. Has actions belonging to it."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="projects", db_index=True,
    )
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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="someday_lists", db_index=True,
    )
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
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="altitudes", db_index=True,
    )
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
    """An action / task / tickler. The load-bearing table.

    Status replaces the old (deleted, completed, is_tickler) boolean combinatorics.
    The composite index on (user, deleted_at, completed_at, status) is the modern
    version of the legacy i_user_deleted_completed_tickler index that kept the old
    app fast at 236K rows.
    """

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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="actions", db_index=True,
    )
    context = models.ForeignKey(
        Context, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="actions", db_index=True,
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="actions", db_index=True,
    )
    someday_list = models.ForeignKey(
        SomedayList, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="actions", db_index=True,
    )

    title = models.CharField(max_length=256)
    notes = models.TextField(blank=True, help_text="Markdown")

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.INBOX, db_index=True,
    )
    starred = models.BooleanField(default=False, db_index=True)

    effort = models.IntegerField(choices=Effort.choices, null=True, blank=True)
    minutes_required = models.PositiveIntegerField(null=True, blank=True)

    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_reminded_at = models.DateTimeField(null=True, blank=True)

    position = models.IntegerField(
        default=0, help_text="Manual reorder within current view",
    )
    extra = models.JSONField(default=dict, blank=True)

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        db_table = "tasks_action"
        ordering = ["position", "-created"]
        indexes = [
            models.Index(
                fields=["user", "deleted_at", "completed_at", "status"],
                name="i_user_del_comp_status",
            ),
            models.Index(fields=["user", "due_date"], name="i_user_due"),
        ]

    def __str__(self) -> str:
        return self.title[:80]


class SavedView(TimeStampedModel):
    """A saved query over actions. Was smarty_smartcontext.

    Renamed for clarity — "smart context" overloaded the meaning of "context".
    Old rule structure (smarty_smartcontextrule + smartcontextrule_contexts M2M)
    collapses into a single JSON `rule` field, evaluated by tasks.saved_views.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="saved_views", db_index=True,
    )
    title = models.CharField(max_length=120)
    feed_slug = models.SlugField(
        max_length=50, null=True, blank=True,
        help_text="Public RSS/iCal feed slug",
    )
    position = models.PositiveIntegerField(default=0)

    # JSON DSL. Example:
    # {
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
