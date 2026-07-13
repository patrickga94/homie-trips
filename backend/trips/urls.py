from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AccommodationViewSet,
    FlightViewSet,
    GroceryItemViewSet,
    ItineraryItemViewSet,
    MealViewSet,
    RentalVehicleViewSet,
    TripViewSet,
)

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
    path(
        "trips/<int:trip_pk>/itinerary/",
        ItineraryItemViewSet.as_view(_list),
        name="itinerary-list",
    ),
    path(
        "trips/<int:trip_pk>/itinerary/<int:pk>/",
        ItineraryItemViewSet.as_view(_detail),
        name="itinerary-detail",
    ),
    path("trips/<int:trip_pk>/meals/", MealViewSet.as_view(_list), name="meal-list"),
    path(
        "trips/<int:trip_pk>/meals/<int:pk>/",
        MealViewSet.as_view(_detail),
        name="meal-detail",
    ),
    path("trips/<int:trip_pk>/rentals/", RentalVehicleViewSet.as_view(_list), name="rental-list"),
    path(
        "trips/<int:trip_pk>/rentals/<int:pk>/",
        RentalVehicleViewSet.as_view(_detail),
        name="rental-detail",
    ),
    path("trips/<int:trip_pk>/grocery/", GroceryItemViewSet.as_view(_list), name="grocery-list"),
    path(
        "trips/<int:trip_pk>/grocery/<int:pk>/",
        GroceryItemViewSet.as_view(_detail),
        name="grocery-detail",
    ),
]

urlpatterns += router.urls
