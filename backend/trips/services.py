from .models import Invitation, TripMembership


def resolve_invitations_for_user(user):
    """Turn any pending invitations addressed to this user's email into
    memberships. Called when a user registers (or could be called on login)."""
    pending = Invitation.objects.filter(
        email__iexact=user.email, status=Invitation.Status.PENDING
    )
    for invite in pending:
        TripMembership.objects.get_or_create(
            trip=invite.trip,
            user=user,
            defaults={"role": TripMembership.Role.MEMBER},
        )
        invite.status = Invitation.Status.ACCEPTED
        invite.save(update_fields=["status"])


def add_member_by_email(trip, email, invited_by):
    """Add a member to a trip by email.

    If a user with that email exists, create the membership immediately and
    return (membership, None). Otherwise create/return a pending invitation
    and return (None, invitation).
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    email = email.strip()
    existing = User.objects.filter(email__iexact=email).first()
    if existing:
        membership, _ = TripMembership.objects.get_or_create(
            trip=trip,
            user=existing,
            defaults={"role": TripMembership.Role.MEMBER},
        )
        return membership, None
    invitation, _ = Invitation.objects.get_or_create(
        trip=trip,
        email=email,
        defaults={"invited_by": invited_by},
    )
    return None, invitation
