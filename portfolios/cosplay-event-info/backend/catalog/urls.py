from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalog.api import CosplayerViewSet, EventViewSet, venues_in_period
from catalog.views import health

router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register("events", EventViewSet, basename="event")
router.register("cosplayers", CosplayerViewSet, basename="cosplayer")

urlpatterns = [
    path("health/", health, name="health"),
    path("venues/", venues_in_period, name="venues"),
    path("", include(router.urls)),
]
