from django.contrib import admin

from .models import Flight, FlightTraveler, Invitation, Trip, TripMembership


class TripMembershipInline(admin.TabularInline):
    model = TripMembership
    extra = 0
    autocomplete_fields = ["user"]


class FlightTravelerInline(admin.TabularInline):
    model = FlightTraveler
    extra = 0
    autocomplete_fields = ["user"]


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ["name", "destination", "start_date", "end_date", "created_by"]
    search_fields = ["name", "destination"]
    inlines = [TripMembershipInline]


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ["__str__", "trip", "departure_airport", "arrival_airport", "departure_time"]
    list_filter = ["trip"]
    inlines = [FlightTravelerInline]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "trip", "status", "invited_by", "created_at"]
    list_filter = ["status"]
    search_fields = ["email"]
