import secrets

from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


def generate_token():
    return secrets.token_urlsafe(32)


class Trip(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    destination = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_trips"
    )
    members = models.ManyToManyField(
        User, through="TripMembership", related_name="trips"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]

    def __str__(self):
        return self.name


class TripMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MEMBER = "member", "Member"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="trip_memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("trip", "user")

    def __str__(self):
        return f"{self.user} in {self.trip} ({self.role})"


class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True, default=generate_token)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="sent_invitations"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("trip", "email")

    def __str__(self):
        return f"Invite {self.email} to {self.trip} ({self.status})"


class Flight(models.Model):
    """A single flight leg. Multiple travelers can share one flight record."""

    class Direction(models.TextChoices):
        ARRIVAL = "arrival", "Arrival"  # getting to the trip
        DEPARTURE = "departure", "Departure"  # heading home

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="flights")
    direction = models.CharField(
        max_length=10, choices=Direction.choices, default=Direction.ARRIVAL
    )
    airline = models.CharField(max_length=100, blank=True)
    flight_number = models.CharField(max_length=20, blank=True)
    departure_airport = models.CharField(max_length=10, blank=True)
    arrival_airport = models.CharField(max_length=10, blank=True)
    departure_time = models.DateTimeField(null=True, blank=True)
    arrival_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    travelers = models.ManyToManyField(
        User, through="FlightTraveler", related_name="flights"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["departure_time", "id"]

    def __str__(self):
        return f"{self.airline} {self.flight_number}".strip() or f"Flight {self.pk}"


class Accommodation(models.Model):
    """Where the group is staying for part or all of a trip (e.g. an Airbnb)."""

    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="accommodations"
    )
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    beds = models.PositiveSmallIntegerField(null=True, blank=True)
    link = models.URLField(blank=True)  # e.g. the Airbnb / VRBO listing
    # Thumbnail, auto-filled from the link's og:image when possible (see
    # services.fetch_og_image); can also be set manually. og:image URLs are
    # often long/signed, hence the generous max_length.
    image_url = models.URLField(max_length=1000, blank=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["check_in", "id"]

    def __str__(self):
        return self.name


class ItineraryItem(models.Model):
    """A scheduled activity on a trip. Grouped by day in the UI; items without
    a day fall into an 'Unscheduled' bucket, and within a day sort by time."""

    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="itinerary_items"
    )
    day = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    title = models.CharField(max_length=200)
    location = models.CharField(max_length=300, blank=True)
    link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Postgres sorts NULLs last on ASC, so timed items come before untimed.
        ordering = ["day", "start_time", "id"]

    def __str__(self):
        return self.title


class RentalVehicle(models.Model):
    """A rental car/van for the trip."""

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="rentals")
    rented_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rentals_booked",
    )
    company = models.CharField(max_length=100, blank=True)  # e.g. Enterprise
    vehicle = models.CharField(max_length=100, blank=True)  # e.g. Jeep Wrangler
    confirmation_code = models.CharField(max_length=40, blank=True)
    pickup_location = models.CharField(max_length=300, blank=True)
    dropoff_location = models.CharField(max_length=300, blank=True)
    pickup_time = models.DateTimeField(null=True, blank=True)
    dropoff_time = models.DateTimeField(null=True, blank=True)
    link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pickup_time", "id"]

    def __str__(self):
        return f"{self.company} {self.vehicle}".strip() or f"Rental {self.pk}"


class Meal(models.Model):
    """A planned meal on a trip, grouped by day (sorted by meal type in the UI)."""

    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACK = "snack", "Snack"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="meals")
    day = models.DateField(null=True, blank=True)
    meal_type = models.CharField(
        max_length=10, choices=MealType.choices, default=MealType.DINNER
    )
    title = models.CharField(max_length=200)
    cooks = models.ManyToManyField(User, related_name="meals_cooking", blank=True)
    ingredients = models.JSONField(default=list, blank=True)  # list of strings
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["day", "id"]  # meal-type order is applied in the frontend

    def __str__(self):
        return self.title


class GroceryItem(models.Model):
    """An item on the trip's shared shopping list."""

    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="grocery_items"
    )
    name = models.CharField(max_length=200)
    quantity = models.CharField(max_length=50, blank=True)  # e.g. "2 lbs"
    category = models.CharField(max_length=50, blank=True)  # e.g. "Produce"
    is_checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "created_at", "id"]

    def __str__(self):
        return self.name


class PointOfInterest(models.Model):
    """A spot the group might want to check out (not a scheduled itinerary item)."""

    class Category(models.TextChoices):
        RESTAURANT = "restaurant", "Restaurant"
        SHOPPING = "shopping", "Shopping"
        ACTIVITY = "activity", "Activity"
        SIGHTSEEING = "sightseeing", "Sightseeing"
        OUTDOORS = "outdoors", "Outdoors"
        NIGHTLIFE = "nightlife", "Nightlife"
        OTHER = "other", "Other"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="pois")
    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    address = models.CharField(max_length=300, blank=True)
    link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    interested = models.ManyToManyField(
        User, related_name="interested_pois", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class PointOfInterestComment(models.Model):
    """A comment on a point of interest, or a reply to another comment.

    Only one level of nesting: replies point at a top-level comment (their
    own `parent` is always null). Only the author may edit or delete it.
    """

    poi = models.ForeignKey(
        PointOfInterest, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="poi_comments"
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Comment by {self.author} on {self.poi}"


class FlightTraveler(models.Model):
    """Through model: one traveler's booking details on a shared flight."""

    flight = models.ForeignKey(
        Flight, on_delete=models.CASCADE, related_name="flight_travelers"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="flight_bookings"
    )
    confirmation_code = models.CharField(max_length=20, blank=True)
    seat = models.CharField(max_length=10, blank=True)

    class Meta:
        unique_together = ("flight", "user")

    def __str__(self):
        return f"{self.user} on {self.flight}"
