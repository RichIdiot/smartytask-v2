"""Top-level URL config."""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", healthz, name="healthz"),
    # path("", include("tasks.urls")),  # uncomment when tasks app has views
]
