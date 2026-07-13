from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Accommodation,
    Flight,
    GroceryItem,
    Invitation,
    ItineraryItem,
    Meal,
    RentalVehicle,
    Trip,
    TripMembership,
)
from .permissions import IsTripMember, IsTripOwner
from .serializers import (
    AccommodationSerializer,
    AddMemberSerializer,
    FlightSerializer,
    GroceryItemSerializer,
    InvitationSerializer,
    ItineraryItemSerializer,
    MealSerializer,
    MembershipSerializer,
    RentalVehicleSerializer,
    TripListSerializer,
    TripSerializer,
)
from .services import add_member_by_email, fetch_og_image


class TripViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTripMember]

    def get_queryset(self):
        return (
            Trip.objects.filter(memberships__user=self.request.user)
            .prefetch_related("memberships__user")
            .distinct()
        )

    def get_serializer_class(self):
        if self.action == "list":
            return TripListSerializer
        return TripSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAuthenticated(), IsTripOwner()]
        return super().get_permissions()

    def perform_create(self, serializer):
        trip = serializer.save(created_by=self.request.user)
        TripMembership.objects.create(
            trip=trip, user=self.request.user, role=TripMembership.Role.OWNER
        )

    @action(detail=True, methods=["get", "post"])
    def members(self, request, pk=None):
        trip = self.get_object()
        if request.method == "GET":
            data = {
                "members": MembershipSerializer(
                    trip.memberships.select_related("user"), many=True
                ).data,
                "pending_invitations": InvitationSerializer(
                    trip.invitations.filter(status="pending"), many=True
                ).data,
            }
            return Response(data)

        # POST: add a member by email.
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership, invitation = add_member_by_email(
            trip, serializer.validated_data["email"], request.user
        )
        if membership:
            return Response(
                {"added": MembershipSerializer(membership).data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"invited": InvitationSerializer(invitation).data},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["delete"], url_path=r"members/(?P<user_id>[^/.]+)")
    def remove_member(self, request, pk=None, user_id=None):
        trip = self.get_object()
        # Only owners can remove others.
        is_owner = trip.memberships.filter(
            user=request.user, role=TripMembership.Role.OWNER
        ).exists()
        if not is_owner and str(request.user.id) != str(user_id):
            raise PermissionDenied("Only owners can remove other members.")
        membership = get_object_or_404(TripMembership, trip=trip, user_id=user_id)
        if membership.role == TripMembership.Role.OWNER and (
            trip.memberships.filter(role=TripMembership.Role.OWNER).count() <= 1
        ):
            raise PermissionDenied("Cannot remove the last owner of a trip.")
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path=r"invitations/(?P<invite_id>[^/.]+)")
    def cancel_invitation(self, request, pk=None, invite_id=None):
        trip = self.get_object()  # enforces trip membership
        invitation = get_object_or_404(Invitation, pk=invite_id, trip=trip)
        invitation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TripScopedMixin:
    """Shared trip lookup for resources nested under /trips/<trip_pk>/.

    Resolves the parent trip from the URL and enforces that the requester is a
    member, for every action (list/retrieve included).
    """

    def get_trip(self):
        if not hasattr(self, "_trip"):
            trip = get_object_or_404(Trip, pk=self.kwargs["trip_pk"])
            if not trip.memberships.filter(user=self.request.user).exists():
                raise PermissionDenied("You are not a member of this trip.")
            self._trip = trip
        return self._trip

    def perform_create(self, serializer):
        serializer.save(trip=self.get_trip())


class FlightViewSet(TripScopedMixin, viewsets.ModelViewSet):
    serializer_class = FlightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_trip().flights.prefetch_related("flight_travelers__user")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Needed by FlightSerializer.validate on create (no instance yet).
        if self.action in ("create", "update", "partial_update"):
            context["trip"] = self.get_trip()
        return context


class AccommodationViewSet(TripScopedMixin, viewsets.ModelViewSet):
    serializer_class = AccommodationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_trip().accommodations.all()

    def perform_create(self, serializer):
        instance = serializer.save(trip=self.get_trip())
        self._maybe_fetch_image(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._maybe_fetch_image(instance)

    @staticmethod
    def _maybe_fetch_image(instance):
        if instance.link and not instance.image_url:
            image = fetch_og_image(instance.link)
            if image:
                instance.image_url = image
                instance.save(update_fields=["image_url"])


class ItineraryItemViewSet(TripScopedMixin, viewsets.ModelViewSet):
    serializer_class = ItineraryItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_trip().itinerary_items.all()


class RentalVehicleViewSet(TripScopedMixin, viewsets.ModelViewSet):
    serializer_class = RentalVehicleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_trip().rentals.select_related("rented_by")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Needed by RentalVehicleSerializer.validate (rented_by membership).
        if self.action in ("create", "update", "partial_update"):
            context["trip"] = self.get_trip()
        return context


class GroceryItemViewSet(TripScopedMixin, viewsets.ModelViewSet):
    serializer_class = GroceryItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_trip().grocery_items.all()


class MealViewSet(TripScopedMixin, viewsets.ModelViewSet):
    serializer_class = MealSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_trip().meals.prefetch_related("cooks")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Needed by MealSerializer.validate (cook membership) on create.
        if self.action in ("create", "update", "partial_update"):
            context["trip"] = self.get_trip()
        return context
