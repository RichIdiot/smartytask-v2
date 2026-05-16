"""Top-level URL config."""
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import include, path


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def root(request):
    if request.user.is_authenticated:
        return redirect("inbox")
    return redirect("accounts:login")


urlpatterns = [
    path("", root, name="root"),
    path("admin/", admin.site.urls),
    path("healthz/", healthz, name="healthz"),
    path("accounts/", include("accounts.urls")),
    path("app/", include("tasks.urls")),
]
