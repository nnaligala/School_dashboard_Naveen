from django.urls import path

from . import health

app_name = "core"

urlpatterns = [
    path("healthz/", health.live, name="healthz"),
    path("readyz/", health.ready, name="readyz"),
]
