from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import (
    Accommodation,
    Flight,
    FlightTraveler,
    Invitation,
    Trip,
    TripMembership,
)

User = get_user_model()


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = TripMembership
        fields = ["id", "user", "role", "joined_at"]


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ["id", "email", "status", "created_at"]


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()


class TripSerializer(serializers.ModelSerializer):
    memberships = MembershipSerializer(many=True, read_only=True)
    my_role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "name",
            "description",
            "destination",
            "start_date",
            "end_date",
            "created_by",
            "created_at",
            "memberships",
            "my_role",
            "member_count",
        ]
        read_only_fields = ["created_by", "created_at"]

    def get_my_role(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        membership = next(
            (m for m in obj.memberships.all() if m.user_id == request.user.id), None
        )
        return membership.role if membership else None

    def get_member_count(self, obj):
        return obj.memberships.count()


class TripListSerializer(TripSerializer):
    """Lighter representation for list views (no nested memberships)."""

    class Meta(TripSerializer.Meta):
        fields = [
            "id",
            "name",
            "destination",
            "start_date",
            "end_date",
            "my_role",
            "member_count",
        ]


class AccommodationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accommodation
        fields = [
            "id",
            "trip",
            "name",
            "address",
            "beds",
            "link",
            "image_url",
            "check_in",
            "check_out",
            "notes",
            "created_at",
        ]
        read_only_fields = ["trip", "created_at"]


class FlightTravelerSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    user_detail = UserSerializer(source="user", read_only=True)

    class Meta:
        model = FlightTraveler
        fields = ["id", "user", "user_detail", "confirmation_code", "seat"]


class FlightSerializer(serializers.ModelSerializer):
    travelers = FlightTravelerSerializer(source="flight_travelers", many=True, required=False)

    class Meta:
        model = Flight
        fields = [
            "id",
            "trip",
            "direction",
            "airline",
            "flight_number",
            "departure_airport",
            "arrival_airport",
            "departure_time",
            "arrival_time",
            "notes",
            "travelers",
            "created_at",
        ]
        read_only_fields = ["trip", "created_at"]

    def validate(self, attrs):
        """Ensure every assigned traveler is actually a member of the trip."""
        travelers = self.initial_data.get("travelers")
        trip = self.instance.trip if self.instance else self.context.get("trip")
        if travelers and trip:
            member_ids = set(trip.memberships.values_list("user_id", flat=True))
            for t in travelers:
                if int(t["user"]) not in member_ids:
                    raise serializers.ValidationError(
                        {"travelers": f"User {t['user']} is not a member of this trip."}
                    )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        travelers = validated_data.pop("flight_travelers", [])
        flight = Flight.objects.create(**validated_data)
        self._sync_travelers(flight, travelers)
        return flight

    @transaction.atomic
    def update(self, instance, validated_data):
        travelers = validated_data.pop("flight_travelers", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if travelers is not None:
            instance.flight_travelers.all().delete()
            self._sync_travelers(instance, travelers)
        return instance

    @staticmethod
    def _sync_travelers(flight, travelers):
        FlightTraveler.objects.bulk_create(
            [
                FlightTraveler(
                    flight=flight,
                    user=t["user"],
                    confirmation_code=t.get("confirmation_code", ""),
                    seat=t.get("seat", ""),
                )
                for t in travelers
            ]
        )
