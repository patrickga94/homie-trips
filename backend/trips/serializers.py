from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import (
    Accommodation,
    Flight,
    FlightTraveler,
    GroceryItem,
    Invitation,
    ItineraryItem,
    Meal,
    PointOfInterest,
    PointOfInterestComment,
    RentalVehicle,
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


class ItineraryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItineraryItem
        fields = [
            "id",
            "trip",
            "day",
            "start_time",
            "end_time",
            "title",
            "location",
            "link",
            "notes",
            "created_at",
        ]
        read_only_fields = ["trip", "created_at"]


class PointOfInterestSerializer(serializers.ModelSerializer):
    interested_count = serializers.SerializerMethodField()
    interested_names = serializers.SerializerMethodField()
    is_interested = serializers.SerializerMethodField()

    class Meta:
        model = PointOfInterest
        fields = [
            "id",
            "trip",
            "name",
            "category",
            "address",
            "link",
            "notes",
            "interested_count",
            "interested_names",
            "is_interested",
            "created_at",
        ]
        read_only_fields = ["trip", "created_at"]

    def get_interested_count(self, obj):
        return len(obj.interested.all())

    def get_interested_names(self, obj):
        return [u.name for u in obj.interested.all()]

    def get_is_interested(self, obj):
        request = self.context.get("request")
        if not request:
            return False
        return any(u.id == request.user.id for u in obj.interested.all())


class PoiCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)
    is_mine = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = PointOfInterestComment
        fields = [
            "id",
            "poi",
            "parent",
            "author_name",
            "is_mine",
            "body",
            "replies",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["poi", "created_at", "updated_at"]

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and obj.author_id == request.user.id)

    def get_replies(self, obj):
        # Replies are only nested under a top-level comment (one level deep).
        if obj.parent_id is not None:
            return []
        return PoiCommentSerializer(
            obj.replies.all(), many=True, context=self.context
        ).data

    def validate_parent(self, value):
        if value is None:
            return value
        poi = self.context.get("poi")
        if poi is not None and value.poi_id != poi.id:
            raise serializers.ValidationError(
                "Reply must be on the same place of interest."
            )
        if value.parent_id is not None:
            raise serializers.ValidationError("Cannot reply to a reply.")
        return value


class GroceryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroceryItem
        fields = ["id", "trip", "name", "quantity", "category", "is_checked", "created_at"]
        read_only_fields = ["trip", "created_at"]


class RentalVehicleSerializer(serializers.ModelSerializer):
    rented_by_detail = UserSerializer(source="rented_by", read_only=True)

    class Meta:
        model = RentalVehicle
        fields = [
            "id",
            "trip",
            "rented_by",
            "rented_by_detail",
            "company",
            "vehicle",
            "confirmation_code",
            "pickup_location",
            "dropoff_location",
            "pickup_time",
            "dropoff_time",
            "link",
            "notes",
            "created_at",
        ]
        read_only_fields = ["trip", "created_at"]

    def validate(self, attrs):
        rented_by = attrs.get("rented_by")
        trip = self.instance.trip if self.instance else self.context.get("trip")
        if rented_by and trip and not trip.memberships.filter(user=rented_by).exists():
            raise serializers.ValidationError(
                {"rented_by": "Must be a member of this trip."}
            )
        return attrs


class MealSerializer(serializers.ModelSerializer):
    cooks = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )
    cook_details = UserSerializer(source="cooks", many=True, read_only=True)

    class Meta:
        model = Meal
        fields = [
            "id",
            "trip",
            "day",
            "meal_type",
            "title",
            "cooks",
            "cook_details",
            "ingredients",
            "notes",
            "created_at",
        ]
        read_only_fields = ["trip", "created_at"]

    def validate_ingredients(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of items.")
        cleaned = []
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each ingredient must be text.")
            item = item.strip()
            if item:
                cleaned.append(item[:100])
        return cleaned[:100]

    def validate(self, attrs):
        cooks = attrs.get("cooks")
        trip = self.instance.trip if self.instance else self.context.get("trip")
        if cooks and trip:
            member_ids = set(trip.memberships.values_list("user_id", flat=True))
            for user in cooks:
                if user.id not in member_ids:
                    raise serializers.ValidationError(
                        {"cooks": f"{user} is not a member of this trip."}
                    )
        return attrs


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
