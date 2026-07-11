from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AccommodationViewSet, FlightViewSet, TripViewSet

router = DefaultRouter()
router.register("trips", TripViewSet, basename="trip")

_list = {"get": "list", "post": "create"}
_detail = {
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
}

urlpatterns = [
    path("trips/<int:trip_pk>/flights/", FlightViewSet.as_view(_list), name="flight-list"),
    path(
        "trips/<int:trip_pk>/flights/<int:pk>/",
        FlightViewSet.as_view(_detail),
        name="flight-detail",
    ),
    path(
        "trips/<int:trip_pk>/accommodations/",
        AccommodationViewSet.as_view(_list),
        name="accommodation-list",
    ),
    path(
        "trips/<int:trip_pk>/accommodations/<int:pk>/",
        AccommodationViewSet.as_view(_detail),
        name="accommodation-detail",
    ),
]

urlpatterns += router.urls
