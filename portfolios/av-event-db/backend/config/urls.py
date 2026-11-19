from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [path("api/", include("events.urls"))]

if settings.ENABLE_ADMIN:
    urlpatterns.append(path("admin/", admin.site.urls))
