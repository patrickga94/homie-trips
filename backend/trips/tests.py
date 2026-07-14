from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Accommodation,
    Flight,
    Invitation,
    PointOfInterest,
    Trip,
    TripMembership,
)
from .services import fetch_og_image

User = get_user_model()


class TripApiTests(APITestCase):
    def setUp(self):
        # Reset throttle counters so rate limits don't leak across tests.
        cache.clear()
        self.alice = User.objects.create_user(email="alice@example.com", password="pw-alice-123")
        self.bob = User.objects.create_user(email="bob@example.com", password="pw-bob-1234")

    def test_creator_becomes_owner(self):
        self.client.force_login(self.alice)
        resp = self.client.post("/api/trips/", {"name": "Beach Week"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        trip = Trip.objects.get(pk=resp.data["id"])
        membership = TripMembership.objects.get(trip=trip, user=self.alice)
        self.assertEqual(membership.role, TripMembership.Role.OWNER)

    def test_non_member_cannot_see_or_retrieve_trip(self):
        trip = Trip.objects.create(name="Alice Trip", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")

        self.client.force_login(self.bob)
        # Not in Bob's list.
        list_resp = self.client.get("/api/trips/")
        self.assertEqual(list_resp.data["count"] if "count" in list_resp.data else len(list_resp.data), 0)
        # Cannot retrieve it directly (queryset excludes it -> 404).
        detail_resp = self.client.get(f"/api/trips/{trip.id}/")
        self.assertEqual(detail_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_owner_cannot_delete_trip(self):
        trip = Trip.objects.create(name="Shared", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        TripMembership.objects.create(trip=trip, user=self.bob, role="member")

        self.client.force_login(self.bob)
        resp = self.client.delete(f"/api/trips/{trip.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Trip.objects.filter(pk=trip.id).exists())

    def test_add_existing_user_as_member(self):
        trip = Trip.objects.create(name="Ski", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")

        self.client.force_login(self.alice)
        resp = self.client.post(
            f"/api/trips/{trip.id}/members/", {"email": "bob@example.com"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TripMembership.objects.filter(trip=trip, user=self.bob).exists())

    def test_invite_unknown_email_resolves_on_registration(self):
        trip = Trip.objects.create(name="Reunion", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")

        self.client.force_login(self.alice)
        resp = self.client.post(
            f"/api/trips/{trip.id}/members/", {"email": "carol@example.com"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(Invitation.objects.filter(trip=trip, email="carol@example.com").exists())

        # Carol registers -> pending invitation becomes a membership.
        self.client.logout()
        reg = self.client.post(
            "/api/auth/register/",
            {"email": "carol@example.com", "password": "pw-carol-123"},
            format="json",
        )
        self.assertEqual(reg.status_code, status.HTTP_201_CREATED)
        carol = User.objects.get(email="carol@example.com")
        self.assertTrue(TripMembership.objects.filter(trip=trip, user=carol).exists())
        self.assertEqual(
            Invitation.objects.get(trip=trip, email="carol@example.com").status, "accepted"
        )

    def test_registration_requires_invitation(self):
        # An uninvited email cannot create an account.
        resp = self.client.post(
            "/api/auth/register/",
            {"email": "stranger@example.com", "password": "pw-stranger-1"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", resp.data)
        self.assertFalse(User.objects.filter(email="stranger@example.com").exists())

    def test_flight_with_multiple_travelers(self):
        trip = Trip.objects.create(name="Vegas", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        TripMembership.objects.create(trip=trip, user=self.bob, role="member")

        self.client.force_login(self.alice)
        payload = {
            "airline": "United",
            "flight_number": "UA123",
            "departure_airport": "SFO",
            "arrival_airport": "LAS",
            "departure_time": "2026-08-01T10:00:00Z",
            "arrival_time": "2026-08-01T11:30:00Z",
            "travelers": [
                {"user": self.alice.id, "confirmation_code": "AAA111", "seat": "12A"},
                {"user": self.bob.id, "confirmation_code": "BBB222", "seat": "12B"},
            ],
        }
        resp = self.client.post(f"/api/trips/{trip.id}/flights/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        flight = Flight.objects.get(pk=resp.data["id"])
        self.assertEqual(flight.travelers.count(), 2)
        self.assertEqual(len(resp.data["travelers"]), 2)

    def test_flight_update_replaces_travelers(self):
        trip = Trip.objects.create(name="Update", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        TripMembership.objects.create(trip=trip, user=self.bob, role="member")

        self.client.force_login(self.alice)
        create = self.client.post(
            f"/api/trips/{trip.id}/flights/",
            {
                "airline": "United",
                "travelers": [
                    {"user": self.alice.id, "confirmation_code": "AAA", "seat": "1A"},
                    {"user": self.bob.id, "confirmation_code": "BBB", "seat": "1B"},
                ],
            },
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, create.data)
        fid = create.data["id"]

        # Edit: rename airline and keep only Alice, with a new seat.
        resp = self.client.patch(
            f"/api/trips/{trip.id}/flights/{fid}/",
            {
                "airline": "Delta",
                "travelers": [{"user": self.alice.id, "confirmation_code": "AAA", "seat": "2C"}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["airline"], "Delta")
        self.assertEqual(len(resp.data["travelers"]), 1)
        self.assertEqual(resp.data["travelers"][0]["seat"], "2C")
        self.assertEqual(Flight.objects.get(pk=fid).travelers.count(), 1)

    def test_flight_direction_defaults_and_persists(self):
        trip = Trip.objects.create(name="Directions", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        self.client.force_login(self.alice)

        r1 = self.client.post(f"/api/trips/{trip.id}/flights/", {"airline": "UA"}, format="json")
        self.assertEqual(r1.data["direction"], "arrival")  # default

        r2 = self.client.post(
            f"/api/trips/{trip.id}/flights/",
            {"airline": "DL", "direction": "departure"},
            format="json",
        )
        self.assertEqual(r2.data["direction"], "departure")

    def test_flight_traveler_must_be_trip_member(self):
        trip = Trip.objects.create(name="NYC", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")

        self.client.force_login(self.alice)
        payload = {
            "airline": "Delta",
            "travelers": [{"user": self.bob.id}],  # Bob is not a member
        }
        resp = self.client.post(f"/api/trips/{trip.id}/flights/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_member_cannot_list_flights(self):
        trip = Trip.objects.create(name="Private", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")

        self.client.force_login(self.bob)
        resp = self.client.get(f"/api/trips/{trip.id}/flights/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    @patch("trips.views.fetch_og_image", return_value="")
    def test_accommodation_crud_and_membership(self, mock_fetch):
        trip = Trip.objects.create(name="Cabin Trip", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")

        self.client.force_login(self.alice)
        create = self.client.post(
            f"/api/trips/{trip.id}/accommodations/",
            {
                "name": "Yosemite Cabin",
                "address": "123 Pine Rd",
                "beds": 4,
                "link": "https://airbnb.com/rooms/123",
                "check_in": "2026-09-01",
                "check_out": "2026-09-05",
            },
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, create.data)
        acc_id = create.data["id"]
        self.assertEqual(Accommodation.objects.get(pk=acc_id).beds, 4)

        # Edit
        patch = self.client.patch(
            f"/api/trips/{trip.id}/accommodations/{acc_id}/",
            {"beds": 6},
            format="json",
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        self.assertEqual(Accommodation.objects.get(pk=acc_id).beds, 6)

        # A non-member cannot list this trip's accommodations.
        self.client.force_login(self.bob)
        resp = self.client.get(f"/api/trips/{trip.id}/accommodations/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    @patch("trips.views.fetch_og_image", return_value="https://img.example.com/pic.jpg")
    def test_accommodation_image_autofilled_from_link(self, mock_fetch):
        trip = Trip.objects.create(name="Trip", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        self.client.force_login(self.alice)
        resp = self.client.post(
            f"/api/trips/{trip.id}/accommodations/",
            {"name": "Cabin", "link": "https://airbnb.com/rooms/1"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["image_url"], "https://img.example.com/pic.jpg")
        mock_fetch.assert_called_once()

    @patch("trips.views.fetch_og_image")
    def test_accommodation_manual_image_not_overwritten(self, mock_fetch):
        trip = Trip.objects.create(name="Trip", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        self.client.force_login(self.alice)
        resp = self.client.post(
            f"/api/trips/{trip.id}/accommodations/",
            {
                "name": "Cabin",
                "link": "https://airbnb.com/rooms/1",
                "image_url": "https://my.photo/x.jpg",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["image_url"], "https://my.photo/x.jpg")
        mock_fetch.assert_not_called()

    def test_fetch_og_image_blocks_internal_urls(self):
        # SSRF guard: never fetch localhost / link-local / non-http schemes.
        self.assertEqual(fetch_og_image("http://localhost/x"), "")
        self.assertEqual(fetch_og_image("http://169.254.169.254/latest/meta-data/"), "")
        self.assertEqual(fetch_og_image("ftp://example.com/file"), "")

    def test_cancel_invitation(self):
        trip = Trip.objects.create(name="Cleanup", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        self.client.force_login(self.alice)
        self.client.post(
            f"/api/trips/{trip.id}/members/", {"email": "typo@example.com"}, format="json"
        )
        inv = Invitation.objects.get(trip=trip, email="typo@example.com")
        resp = self.client.delete(f"/api/trips/{trip.id}/invitations/{inv.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Invitation.objects.filter(pk=inv.id).exists())

    def test_login_is_rate_limited(self):
        # 'login' scope allows 10/min; the 11th attempt from the same client is
        # throttled (429), which blunts password brute-forcing.
        payload = {"email": "alice@example.com", "password": "wrong-password"}
        codes = [
            self.client.post("/api/auth/login/", payload, format="json").status_code
            for _ in range(11)
        ]
        self.assertEqual(codes[0], status.HTTP_400_BAD_REQUEST)
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, codes)

    def test_itinerary_crud_and_membership(self):
        trip = Trip.objects.create(name="Yellowstone", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        self.client.force_login(self.alice)
        resp = self.client.post(
            f"/api/trips/{trip.id}/itinerary/",
            {
                "title": "Old Faithful",
                "day": "2026-09-02",
                "start_time": "09:30",
                "location": "Old Faithful, WY",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["title"], "Old Faithful")
        self.assertEqual(resp.data["start_time"], "09:30:00")

        # Non-member is blocked.
        self.client.force_login(self.bob)
        blocked = self.client.get(f"/api/trips/{trip.id}/itinerary/")
        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN)

    def test_meal_crud_with_cooks_and_ingredients(self):
        trip = Trip.objects.create(name="Cabin Cooking", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        TripMembership.objects.create(trip=trip, user=self.bob, role="member")
        self.client.force_login(self.alice)
        resp = self.client.post(
            f"/api/trips/{trip.id}/meals/",
            {
                "title": "Tacos",
                "day": "2026-09-02",
                "meal_type": "dinner",
                "cooks": [self.alice.id, self.bob.id],
                "ingredients": ["tortillas", " beans ", ""],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(len(resp.data["cooks"]), 2)
        self.assertEqual(len(resp.data["cook_details"]), 2)
        self.assertEqual(resp.data["ingredients"], ["tortillas", "beans"])

    def test_meal_cook_must_be_trip_member(self):
        trip = Trip.objects.create(name="Solo", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        self.client.force_login(self.alice)
        resp = self.client.post(
            f"/api/trips/{trip.id}/meals/",
            {"title": "Soup", "cooks": [self.bob.id]},  # Bob isn't a member
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rental_crud_and_membership(self):
        trip = Trip.objects.create(name="Road Trip", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        self.client.force_login(self.alice)
        resp = self.client.post(
            f"/api/trips/{trip.id}/rentals/",
            {
                "company": "Enterprise",
                "vehicle": "Jeep Wrangler",
                "pickup_location": "SLC Airport",
                "pickup_time": "2026-09-01T12:00:00Z",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["vehicle"], "Jeep Wrangler")

        self.client.force_login(self.bob)
        blocked = self.client.get(f"/api/trips/{trip.id}/rentals/")
        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN)

    def test_grocery_crud_and_toggle(self):
        trip = Trip.objects.create(name="Shopping", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        self.client.force_login(self.alice)
        created = self.client.post(
            f"/api/trips/{trip.id}/grocery/",
            {"name": "Eggs", "quantity": "2 dozen", "category": "Dairy"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertFalse(created.data["is_checked"])
        item_id = created.data["id"]

        toggled = self.client.patch(
            f"/api/trips/{trip.id}/grocery/{item_id}/", {"is_checked": True}, format="json"
        )
        self.assertEqual(toggled.status_code, status.HTTP_200_OK)
        self.assertTrue(toggled.data["is_checked"])

        # Non-member blocked.
        self.client.force_login(self.bob)
        blocked = self.client.get(f"/api/trips/{trip.id}/grocery/")
        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN)

    def test_poi_crud_and_interest_toggle(self):
        trip = Trip.objects.create(name="Explore", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        self.client.force_login(self.alice)
        created = self.client.post(
            f"/api/trips/{trip.id}/pois/",
            {"name": "Taco Stand", "category": "restaurant", "address": "Moab, UT"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(created.data["interested_count"], 0)
        self.assertFalse(created.data["is_interested"])
        poi_id = created.data["id"]

        # Toggle interest on.
        on = self.client.post(f"/api/trips/{trip.id}/pois/{poi_id}/toggle_interest/")
        self.assertEqual(on.status_code, status.HTTP_200_OK)
        self.assertTrue(on.data["is_interested"])
        self.assertEqual(on.data["interested_count"], 1)

        # Toggle back off.
        off = self.client.post(f"/api/trips/{trip.id}/pois/{poi_id}/toggle_interest/")
        self.assertEqual(off.data["interested_count"], 0)
        self.assertFalse(off.data["is_interested"])

    def test_poi_comments_replies_and_author_only_edits(self):
        trip = Trip.objects.create(name="Explore", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        TripMembership.objects.create(trip=trip, user=self.bob, role="member")
        self.client.force_login(self.alice)
        poi = self.client.post(
            f"/api/trips/{trip.id}/pois/",
            {"name": "Taco Stand", "category": "restaurant"},
            format="json",
        ).data
        base = f"/api/trips/{trip.id}/pois/{poi['id']}/comments/"

        # Alice posts a top-level comment.
        comment = self.client.post(base, {"body": "Looks great"}, format="json")
        self.assertEqual(comment.status_code, status.HTTP_201_CREATED, comment.data)
        cid = comment.data["id"]
        self.assertEqual(comment.data["author_name"], self.alice.name)
        self.assertTrue(comment.data["is_mine"])

        # Bob replies to it.
        self.client.force_login(self.bob)
        reply = self.client.post(
            base, {"body": "Agreed", "parent": cid}, format="json"
        )
        self.assertEqual(reply.status_code, status.HTTP_201_CREATED, reply.data)
        rid = reply.data["id"]

        # Listing returns top-level comments with replies nested.
        listing = self.client.get(base)
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(len(listing.data[0]["replies"]), 1)
        self.assertEqual(listing.data[0]["replies"][0]["author_name"], self.bob.name)
        # is_mine reflects the requester (Bob sees Alice's comment as not his).
        self.assertFalse(listing.data[0]["is_mine"])
        self.assertTrue(listing.data[0]["replies"][0]["is_mine"])

        # Bob cannot edit or delete Alice's comment.
        blocked = self.client.patch(
            f"{base}{cid}/", {"body": "hijack"}, format="json"
        )
        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN)
        blocked_del = self.client.delete(f"{base}{cid}/")
        self.assertEqual(blocked_del.status_code, status.HTTP_403_FORBIDDEN)

        # Bob can edit his own reply.
        edited = self.client.patch(
            f"{base}{rid}/", {"body": "Totally agreed"}, format="json"
        )
        self.assertEqual(edited.status_code, status.HTTP_200_OK)
        self.assertEqual(edited.data["body"], "Totally agreed")

        # You cannot reply to a reply (only one level of nesting).
        nested = self.client.post(
            base, {"body": "nope", "parent": rid}, format="json"
        )
        self.assertEqual(nested.status_code, status.HTTP_400_BAD_REQUEST)

        # Alice deletes her comment; its reply cascades away.
        self.client.force_login(self.alice)
        deleted = self.client.delete(f"{base}{cid}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(self.client.get(base).data), 0)

    def test_non_member_cannot_comment_on_poi(self):
        trip = Trip.objects.create(name="Explore", created_by=self.alice)
        TripMembership.objects.create(trip=trip, user=self.alice, role="owner")
        poi = PointOfInterest.objects.create(trip=trip, name="Taco Stand")
        self.client.force_login(self.bob)
        resp = self.client.post(
            f"/api/trips/{trip.id}/pois/{poi.id}/comments/",
            {"body": "sneaky"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_authentication_required(self):
        resp = self.client.get("/api/trips/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_profile(self):
        self.client.force_login(self.alice)
        resp = self.client.patch(
            "/api/auth/me/",
            {
                "first_name": "Alice",
                "last_name": "Smith",
                "preferred_name": "Al",
                "dietary_restrictions": ["vegetarian", " peanut allergy ", ""],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["preferred_name"], "Al")
        self.assertEqual(resp.data["name"], "Al")
        # Whitespace trimmed and empty entries dropped.
        self.assertEqual(resp.data["dietary_restrictions"], ["vegetarian", "peanut allergy"])

    def test_profile_email_is_readonly(self):
        self.client.force_login(self.alice)
        resp = self.client.patch(
            "/api/auth/me/", {"email": "hacker@example.com"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, "alice@example.com")
