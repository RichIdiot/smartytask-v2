from django.contrib import admin

from .models import Action, Altitude, Context, Project, SavedView, SomedayList


@admin.register(Context)
class ContextAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "parent", "is_active", "position")
    list_filter = ("is_active",)
    search_fields = ("title", "user__email")
    raw_id_fields = ("user", "parent")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "completed_at", "due_date", "deleted_at")
    list_filter = ("completed_at", "deleted_at")
    search_fields = ("title", "user__email")
    raw_id_fields = ("user",)


@admin.register(SomedayList)
class SomedayListAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "position")
    search_fields = ("title", "user__email")
    raw_id_fields = ("user",)


@admin.register(Altitude)
class AltitudeAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "depth", "is_collapsed")
    search_fields = ("title", "user__email")
    raw_id_fields = ("user",)


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "context", "project", "starred", "due_date", "deleted_at")
    list_filter = ("status", "starred", "effort", "deleted_at")
    search_fields = ("title", "notes", "user__email")
    raw_id_fields = ("user", "context", "project", "someday_list")


@admin.register(SavedView)
class SavedViewAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "feed_slug", "position")
    search_fields = ("title", "user__email")
    raw_id_fields = ("user",)
