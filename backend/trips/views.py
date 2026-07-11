from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Flight, Trip, TripMembership
from .permissions import IsTripMember, IsTripOwner
from .serializers import (
    AddMemberSerializer,
    FlightSerializer,
    InvitationSerializer,
    MembershipSerializer,
    TripListSerializer,
    TripSerializer,
)
from .services import add_member_by_email


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


class FlightViewSet(viewsets.ModelViewSet):
    serializer_class = FlightSerializer
    permission_classes = [IsAuthenticated]

    def get_trip(self):
        if not hasattr(self, "_trip"):
            trip = get_object_or_404(Trip, pk=self.kwargs["trip_pk"])
            if not trip.memberships.filter(user=self.request.user).exists():
                raise PermissionDenied("You are not a member of this trip.")
            self._trip = trip
        return self._trip

    def get_queryset(self):
        # Enforces trip membership for every action (list/retrieve included).
        trip = self.get_trip()
        return trip.flights.prefetch_related("flight_travelers__user")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Needed by FlightSerializer.validate on create (no instance yet).
        if self.action in ("create", "update", "partial_update"):
            context["trip"] = self.get_trip()
        return context

    def perform_create(self, serializer):
        serializer.save(trip=self.get_trip())
