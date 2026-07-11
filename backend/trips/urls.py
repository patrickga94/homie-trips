from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import FlightViewSet, TripViewSet

router = DefaultRouter()
router.register("trips", TripViewSet, basename="trip")

flight_list = FlightViewSet.as_view({"get": "list", "post": "create"})
flight_detail = FlightViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)

urlpatterns = [
    path("trips/<int:trip_pk>/flights/", flight_list, name="flight-list"),
    path("trips/<int:trip_pk>/flights/<int:pk>/", flight_detail, name="flight-detail"),
]

urlpatterns += router.urls
