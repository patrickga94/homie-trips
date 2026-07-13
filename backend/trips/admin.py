from django.contrib import admin

from .models import (
    Accommodation,
    Flight,
    FlightTraveler,
    GroceryItem,
    Invitation,
    ItineraryItem,
    Meal,
    RentalVehicle,
    Trip,
    TripMembership,
)


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


@admin.register(Accommodation)
class AccommodationAdmin(admin.ModelAdmin):
    list_display = ["name", "trip", "check_in", "check_out", "beds"]
    list_filter = ["trip"]
    search_fields = ["name", "address"]


@admin.register(ItineraryItem)
class ItineraryItemAdmin(admin.ModelAdmin):
    list_display = ["title", "trip", "day", "start_time"]
    list_filter = ["trip"]
    search_fields = ["title", "location"]


@admin.register(GroceryItem)
class GroceryItemAdmin(admin.ModelAdmin):
    list_display = ["name", "trip", "quantity", "category", "is_checked"]
    list_filter = ["trip", "is_checked"]
    search_fields = ["name"]


@admin.register(RentalVehicle)
class RentalVehicleAdmin(admin.ModelAdmin):
    list_display = ["__str__", "trip", "pickup_time", "dropoff_time"]
    list_filter = ["trip"]
    search_fields = ["company", "vehicle"]


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ["title", "trip", "day", "meal_type"]
    list_filter = ["trip", "meal_type"]
    search_fields = ["title"]
    autocomplete_fields = ["cooks"]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "trip", "status", "invited_by", "created_at"]
    list_filter = ["status"]
    search_fields = ["email"]
