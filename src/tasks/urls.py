"""Task URLs — full pages + HTMX endpoints."""
from django.urls import path

from . import views

urlpatterns = [
    # Pages
    path("", views.inbox, name="inbox"),
    path("next/", views.next_actions, name="next_actions"),

    # HTMX endpoints
    path("actions/new/", views.action_create, name="action_create"),
    path("actions/<uuid:pk>/star/", views.action_toggle_star, name="action_toggle_star"),
    path("actions/<uuid:pk>/complete/", views.action_complete, name="action_complete"),
    path("actions/<uuid:pk>/delete/", views.action_delete, name="action_delete"),
    path("actions/<uuid:pk>/edit/", views.action_edit, name="action_edit"),
    path("actions/<uuid:pk>/title/", views.action_update_title, name="action_update_title"),
    path("actions/<uuid:pk>/process/", views.action_move_to_next, name="action_move_to_next"),
]
