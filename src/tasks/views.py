"""Views for the tasks app.

Pages (Inbox, Next Actions, Projects, Project detail) plus HTMX partials for
action and project CRUD. HTMX partial endpoints return small fragments; full-page
requests render the full template.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import QuickAddActionForm, QuickAddProjectForm
from .models import Action, Context, Project


# ---------- helpers ----------

def _counts_for(user) -> dict[str, int]:
    """Sidebar counts. One action aggregate + one project count."""
    qs = Action.objects.filter(user=user, deleted_at__isnull=True)
    agg = qs.aggregate(
        inbox=Count("id", filter=Q(status=Action.Status.INBOX, completed_at__isnull=True)),
        next=Count("id", filter=Q(status=Action.Status.NEXT, completed_at__isnull=True)),
        someday=Count("id", filter=Q(status=Action.Status.SOMEDAY, completed_at__isnull=True)),
        tickler=Count("id", filter=Q(status=Action.Status.TICKLER, completed_at__isnull=True)),
        completed=Count("id", filter=Q(completed_at__isnull=False)),
    )
    agg["projects"] = Project.objects.filter(
        user=user, deleted_at__isnull=True, completed_at__isnull=True,
    ).count()
    return agg


def _is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


def _render_row(request, action: Action) -> HttpResponse:
    return render(request, "tasks/_action_row.html", {"a": action})


def _render_project_row(request, project: Project) -> HttpResponse:
    return render(request, "tasks/_project_row.html", {"p": project})


def _get_user_project(user, pk) -> Project | None:
    """Return user's active project by pk or None."""
    return Project.objects.active().filter(user=user, pk=pk).first()


# ---------- pages: actions ----------

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


# ---------- pages: projects ----------

@login_required
def project_list(request: HttpRequest) -> HttpResponse:
    """All active projects + a small completed section below."""
    base = Project.objects.active().filter(user=request.user).annotate(
        action_count=Count(
            "actions",
            filter=Q(actions__deleted_at__isnull=True, actions__completed_at__isnull=True),
        ),
    )
    active = base.filter(completed_at__isnull=True).order_by("position", "-created")
    completed = base.filter(completed_at__isnull=False).order_by("-completed_at")[:25]

    return render(
        request,
        "tasks/projects.html",
        {
            "active_projects": active,
            "completed_projects": completed,
            "form": QuickAddProjectForm(),
            "counts": _counts_for(request.user),
            "page_title": "Projects",
            "page_subtitle": "Outcomes that take more than one step.",
        },
    )


@login_required
def project_detail(request: HttpRequest, pk) -> HttpResponse:
    project = get_object_or_404(Project.objects.active(), pk=pk, user=request.user)
    actions = (
        Action.objects.active()
        .filter(user=request.user, project=project, completed_at__isnull=True)
        .select_related("context")
        .order_by("position", "-created")
    )
    completed_actions = (
        Action.objects.active()
        .filter(user=request.user, project=project, completed_at__isnull=False)
        .select_related("context")
        .order_by("-completed_at")[:25]
    )
    return render(
        request,
        "tasks/project_detail.html",
        {
            "project": project,
            "actions": actions,
            "completed_actions": completed_actions,
            "form": QuickAddActionForm(),
            "counts": _counts_for(request.user),
            "page_title": project.title,
            "page_subtitle": "Project actions",
        },
    )


# ---------- HTMX endpoints: actions ----------

@login_required
@require_POST
def action_create(request: HttpRequest) -> HttpResponse:
    """POST a new action from the quick-add form. Returns the new row as a fragment.

    Optional: status (default INBOX), project_id (scopes the action to a project).
    """
    form = QuickAddActionForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Invalid input")

    target_status = request.POST.get("status") or Action.Status.INBOX
    if target_status not in dict(Action.Status.choices):
        target_status = Action.Status.INBOX

    project = None
    project_id = request.POST.get("project_id")
    if project_id:
        project = _get_user_project(request.user, project_id)
        if project is None:
            return HttpResponseBadRequest("Unknown project")

    action = form.save(commit=False)
    action.user = request.user
    action.status = target_status
    if project is not None:
        action.project = project
    action.save()

    response = _render_row(request, action)
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
    return HttpResponse("")


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


# ---------- HTMX endpoints: projects ----------

@login_required
@require_POST
def project_create(request: HttpRequest) -> HttpResponse:
    """POST a new project from the quick-add form. Returns the new row as a fragment."""
    form = QuickAddProjectForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Invalid input")
    project = form.save(commit=False)
    project.user = request.user
    project.save()
    # Annotate with action_count for the row partial
    project.action_count = 0
    response = _render_project_row(request, project)
    response["HX-Trigger"] = "counts:update"
    return response


@login_required
@require_GET
def project_edit(request: HttpRequest, pk) -> HttpResponse:
    project = get_object_or_404(Project.objects.active(), pk=pk, user=request.user)
    if request.GET.get("cancel") == "1":
        # Need action_count for the row
        project.action_count = Action.objects.active().filter(
            user=request.user, project=project, completed_at__isnull=True,
        ).count()
        return _render_project_row(request, project)
    return render(request, "tasks/_project_edit.html", {"p": project})


@login_required
@require_POST
def project_update_title(request: HttpRequest, pk) -> HttpResponse:
    project = get_object_or_404(Project.objects.active(), pk=pk, user=request.user)
    title = (request.POST.get("title") or "").strip()
    if not title:
        return HttpResponseBadRequest("Title required")
    project.title = title[:256]
    project.save(update_fields=["title", "modified"])
    project.action_count = Action.objects.active().filter(
        user=request.user, project=project, completed_at__isnull=True,
    ).count()
    return _render_project_row(request, project)


@login_required
@require_POST
def project_complete_toggle(request: HttpRequest, pk) -> HttpResponse:
    project = get_object_or_404(Project.objects.active(), pk=pk, user=request.user)
    if project.completed_at:
        project.completed_at = None
    else:
        project.completed_at = timezone.now()
    project.save(update_fields=["completed_at", "modified"])
    # Row disappears from the active list when completed
    if project.completed_at:
        return HttpResponse("")
    project.action_count = Action.objects.active().filter(
        user=request.user, project=project, completed_at__isnull=True,
    ).count()
    return _render_project_row(request, project)


@login_required
@require_POST
def project_delete(request: HttpRequest, pk) -> HttpResponse:
    project = get_object_or_404(Project.objects.active(), pk=pk, user=request.user)
    project.deleted_at = timezone.now()
    project.save(update_fields=["deleted_at", "modified"])
    return HttpResponse("")
