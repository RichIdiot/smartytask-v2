"""Evaluator for SavedView.rule JSON DSL.

A rule is a dict; calling apply_rule(queryset, rule) returns a filtered queryset.
Empty / missing keys mean "no constraint". Unknown keys are ignored (forward-compat).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import QuerySet
from django.utils import timezone

from .models import Action


def apply_rule(qs: QuerySet[Action], rule: dict[str, Any]) -> QuerySet[Action]:
    if not rule:
        return qs

    # Effort: list of integer choices, e.g. [1, 2]
    if effort_in := rule.get("effort_in"):
        qs = qs.filter(effort__in=effort_in)

    # Time bands derived from minutes_required
    if time_band_in := rule.get("time_band_in"):
        # Convention: low <= 15, 15 < medium <= 60, high > 60
        bands = []
        if "low" in time_band_in:
            bands.append(("minutes_required__lte", 15))
        if "medium" in time_band_in:
            qs = qs.filter(minutes_required__gt=15, minutes_required__lte=60)
        if "high" in time_band_in:
            qs = qs.filter(minutes_required__gt=60)
        for f, v in bands:
            qs = qs.filter(**{f: v})

    # Starred: True, False, or omitted
    if "starred" in rule:
        qs = qs.filter(starred=bool(rule["starred"]))

    # Context filter
    if rule.get("use_context_filter") and (context_in := rule.get("context_in")):
        qs = qs.filter(context_id__in=context_in)

    # Date windows (relative to "now")
    now = timezone.now()
    today = now.date()

    if (days := rule.get("created_within_days")) is not None:
        qs = qs.filter(created__gte=now - timedelta(days=int(days)))
    if (days := rule.get("created_more_than_days_ago")) is not None:
        qs = qs.filter(created__lte=now - timedelta(days=int(days)))
    if (days := rule.get("due_within_days")) is not None:
        qs = qs.filter(due_date__lte=today + timedelta(days=int(days)), due_date__isnull=False)
    if (days := rule.get("due_more_than_days_ago")) is not None:
        qs = qs.filter(due_date__lte=today - timedelta(days=int(days)))

    # Status filter
    if status_in := rule.get("status_in"):
        qs = qs.filter(status__in=status_in)

    return qs
