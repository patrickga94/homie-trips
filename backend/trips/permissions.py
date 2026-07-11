from rest_framework import permissions

from .models import Trip, TripMembership


class IsTripMember(permissions.BasePermission):
    """Allow access only to members of the trip.

    Works for both Trip objects and trip-scoped objects (which expose a
    `.trip` attribute). List/create access is additionally constrained by
    each viewset filtering its queryset to the requester's trips.
    """

    def has_object_permission(self, request, view, obj):
        trip = obj if isinstance(obj, Trip) else getattr(obj, "trip", None)
        if trip is None:
            return False
        return TripMembership.objects.filter(
            trip=trip, user=request.user
        ).exists()


class IsTripOwner(permissions.BasePermission):
    """Allow only trip owners (used for destructive trip-level actions)."""

    def has_object_permission(self, request, view, obj):
        trip = obj if isinstance(obj, Trip) else getattr(obj, "trip", None)
        if trip is None:
            return False
        return TripMembership.objects.filter(
            trip=trip, user=request.user, role=TripMembership.Role.OWNER
        ).exists()
