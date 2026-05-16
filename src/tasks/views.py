"""Views for the tasks app.

Two full pages (Inbox, Next Actions) plus HTMX partials for action CRUD.
HTMX partial endpoints return small fragments; full-page requests render
the full template.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import QuickAddActionForm
from .models import Action, Context


# ---------- helpers ----------

def _counts_for(user) -> dict[str, int]:
    """Sidebar counts. One query."""
    qs = Action.objects.filter(user=user, deleted_at__isnull=True)
    agg = qs.aggregate(
        inbox=Count("id", filter=Q(status=Action.Status.INBOX, completed_at__isnull=True)),
        next=Count("id", filter=Q(status=Action.Status.NEXT, completed_at__isnull=True)),
        someday=Count("id", filter=Q(status=Action.Status.SOMEDAY, completed_at__isnull=True)),
        tickler=Count("id", filter=Q(status=Action.Status.TICKLER, completed_at__isnull=True)),
        completed=Count("id", filter=Q(completed_at__isnull=False)),
    )
    return agg


def _is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


def _render_row(request, action: Action) -> HttpResponse:
    return render(request, "tasks/_action_row.html", {"a": action})


# ---------- pages ----------

@login_required
def inbox(request: HttpRequest) -> HttpResponse:
    actions = (
        Action.objects.active()
        .filter(user=request.user, status=Action.Status.INBOX, completed_at__isnull=True)
        .order_by("-created")
    )
    return render(
        request,
        "tasks/inbox.html",
        {
            "actions": actions,
            "form": QuickAddActionForm(),
            "counts": _counts_for(request.user),
            "page_title": "Inbox",
            "page_subtitle": "Capture everything. Process later.",
        },
    )


@login_required
def next_actions(request: HttpRequest) -> HttpResponse:
    qs = (
        Action.objects.active()
        .filter(
            user=request.user,
            status=Action.Status.NEXT,
            completed_at__isnull=True,
        )
        .select_related("context", "project")
        .order_by("context__position", "context__title", "position", "-created")
    )

    # Group by context — None bucket first as "No context"
    groups: dict[Context | None, list[Action]] = {}
    for action in qs:
        groups.setdefault(action.context, []).append(action)

    # Order: contexts with actions first, then "No context"
    ordered_groups = [
        (ctx, items)
        for ctx, items in sorted(
            groups.items(),
            key=lambda kv: (kv[0] is None, kv[0].position if kv[0] else 0, kv[0].title if kv[0] else ""),
        )
    ]

    return render(
        request,
        "tasks/next_actions.html",
        {
            "groups": ordered_groups,
            "form": QuickAddActionForm(),
            "counts": _counts_for(request.user),
            "page_title": "Next Actions",
            "page_subtitle": "What needs doing now, grouped by where.",
        },
    )


# ---------- HTMX endpoints ----------

@login_required
@require_POST
def action_create(request: HttpRequest) -> HttpResponse:
    """POST a new action from the quick-add form. Returns the new row as a fragment."""
    form = QuickAddActionForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Invalid input")

    # Status defaults to INBOX from the model; explicit on the next-actions page.
    target_status = request.POST.get("status") or Action.Status.INBOX
    if target_status not in dict(Action.Status.choices):
        target_status = Action.Status.INBOX

    action = form.save(commit=False)
    action.user = request.user
    action.status = target_status
    action.save()

    response = _render_row(request, action)
    # Bump sidebar counts via out-of-band swap
    response["HX-Trigger"] = "counts:update"
    return response


@login_required
@require_POST
def action_toggle_star(request: HttpRequest, pk) -> HttpResponse:
    action = get_object_or_404(Action.objects.active(), pk=pk, user=request.user)
    action.starred = not action.starred
    action.save(update_fields=["starred", "modified"])
    return _render_row(request, action)


@login_required
@require_POST
def action_complete(request: HttpRequest, pk) -> HttpResponse:
    action = get_object_or_404(Action.objects.active(), pk=pk, user=request.user)
    if action.completed_at:
        action.completed_at = None
        action.status = Action.Status.NEXT
    else:
        action.completed_at = timezone.now()
        action.status = Action.Status.COMPLETED
    action.save(update_fields=["completed_at", "status", "modified"])
    # When completing from a view, the row disappears
    if action.completed_at and not _is_htmx_keep_row(request):
        return HttpResponse("")
    return _render_row(request, action)


def _is_htmx_keep_row(request: HttpRequest) -> bool:
    return request.GET.get("keep") == "1"


@login_required
@require_POST
def action_delete(request: HttpRequest, pk) -> HttpResponse:
    action = get_object_or_404(Action.objects.active(), pk=pk, user=request.user)
    action.deleted_at = timezone.now()
    action.save(update_fields=["deleted_at", "modified"])
    return HttpResponse("")  # row vanishes


@login_required
@require_GET
def action_edit(request: HttpRequest, pk) -> HttpResponse:
    action = get_object_or_404(Action.objects.active(), pk=pk, user=request.user)
    if request.GET.get("cancel") == "1":
        return _render_row(request, action)
    return render(request, "tasks/_action_edit.html", {"a": action})


@login_required
@require_POST
def action_update_title(request: HttpRequest, pk) -> HttpResponse:
    action = get_object_or_404(Action.objects.active(), pk=pk, user=request.user)
    title = (request.POST.get("title") or "").strip()
    if not title:
        return HttpResponseBadRequest("Title required")
    action.title = title[:256]
    action.save(update_fields=["title", "modified"])
    return _render_row(request, action)


@login_required
@require_POST
def action_move_to_next(request: HttpRequest, pk) -> HttpResponse:
    """Process an Inbox item: move it to Next Actions."""
    action = get_object_or_404(Action.objects.active(), pk=pk, user=request.user)
    action.status = Action.Status.NEXT
    action.save(update_fields=["status", "modified"])
    return HttpResponse("")  # row vanishes from Inbox
