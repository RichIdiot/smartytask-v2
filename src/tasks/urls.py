"""Task URLs — full pages + HTMX endpoints."""
from django.urls import path

from . import views

urlpatterns = [
    # Pages
    path("", views.inbox, name="inbox"),
    path("next/", views.next_actions, name="next_actions"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/<uuid:pk>/", views.project_detail, name="project_detail"),

    # HTMX endpoints — actions
    path("actions/new/", views.action_create, name="action_create"),
    path("actions/<uuid:pk>/star/", views.action_toggle_star, name="action_toggle_star"),
    path("actions/<uuid:pk>/complete/", views.action_complete, name="action_complete"),
    path("actions/<uuid:pk>/delete/", views.action_delete, name="action_delete"),
    path("actions/<uuid:pk>/edit/", views.action_edit, name="action_edit"),
    path("actions/<uuid:pk>/title/", views.action_update_title, name="action_update_title"),
    path("actions/<uuid:pk>/process/", views.action_move_to_next, name="action_move_to_next"),

    # HTMX endpoints — projects
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<uuid:pk>/edit/", views.project_edit, name="project_edit"),
    path("projects/<uuid:pk>/title/", views.project_update_title, name="project_update_title"),
    path("projects/<uuid:pk>/complete/", views.project_complete_toggle, name="project_complete_toggle"),
    path("projects/<uuid:pk>/delete/", views.project_delete, name="project_delete"),
]
