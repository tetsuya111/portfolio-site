from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("events", views.EventViewSet, basename="event")

urlpatterns = [
    path("health/", views.health),
    path("map/venues/", views.map_venues),
    path("", include(router.urls)),
]
