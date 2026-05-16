"""Template tags for nav items and small UI primitives."""
from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def nav_item(context, url_name: str, label: str, count: int | None = None) -> str:
    """Sidebar nav link with active highlight + optional count badge."""
    request = context["request"]
    href = reverse(url_name)
    is_active = request.path == href or request.path.startswith(href + "/")
    classes = (
        "flex items-center justify-between rounded-lg px-4 py-3 text-[16px] "
        "transition-colors "
        + (
            "bg-blue-600/15 text-white font-semibold"
            if is_active
            else "text-slate-300 hover:bg-slate-800 hover:text-white"
        )
    )
    badge = ""
    if count:
        badge = (
            f'<span class="inline-flex items-center justify-center min-w-[28px] '
            f'rounded-full bg-slate-700 text-slate-100 px-2.5 py-0.5 text-[13px] '
            f'font-medium">{count}</span>'
        )
    return template.Template(
        f'<a href="{href}" class="{classes}"><span>{label}</span>{badge}</a>'
    ).render(template.Context({}))


@register.simple_tag
def nav_item_disabled(label: str, count: int | None = None) -> str:
    """Placeholder nav item — disabled for v1."""
    badge = ""
    if count:
        badge = (
            f'<span class="inline-flex items-center justify-center min-w-[28px] '
            f'rounded-full bg-slate-800 text-slate-400 px-2.5 py-0.5 text-[13px]">{count}</span>'
        )
    return template.Template(
        f'<div class="flex items-center justify-between rounded-lg px-4 py-3 '
        f'text-[16px] text-slate-500 cursor-not-allowed" title="Coming soon">'
        f'<span>{label}</span>{badge}</div>'
    ).render(template.Context({}))


@register.simple_tag(takes_context=True)
def nav_pill(context, url_name: str, label: str, count: int | None = None) -> str:
    """Mobile horizontal-scroll pill."""
    request = context["request"]
    href = reverse(url_name)
    is_active = request.path == href
    classes = (
        "inline-flex items-center gap-2 rounded-full px-4 py-2 text-[15px] "
        "transition-colors "
        + (
            "bg-blue-600 text-white font-semibold"
            if is_active
            else "bg-slate-100 text-slate-700 hover:bg-slate-200"
        )
    )
    badge = ""
    if count:
        badge = (
            f'<span class="inline-flex items-center justify-center rounded-full '
            f'bg-white/20 px-2 text-[12px]">{count}</span>'
        )
    return template.Template(
        f'<a href="{href}" class="{classes}">{label}{badge}</a>'
    ).render(template.Context({}))
