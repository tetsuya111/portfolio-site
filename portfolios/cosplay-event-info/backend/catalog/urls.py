from django.urls import path

from catalog.views import health

urlpatterns = [
    path("health/", health, name="health"),
]
