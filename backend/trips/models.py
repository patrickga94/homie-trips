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

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="flights")
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
