import html
import ipaddress
import re
import socket
import urllib.request
from urllib.parse import urlparse

from .models import Invitation, TripMembership

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)
_OG_IMAGE_PATTERNS = (
    r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::url)?["\']',
    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
)


def _is_safe_public_url(url):
    """Guard against SSRF: only http(s) to public hosts (no localhost/private IPs)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return False
    return True


def fetch_og_image(url, timeout=4):
    """Best-effort fetch of a page's og:image (or twitter:image). Returns '' on
    any failure so callers can treat it as "no thumbnail available"."""
    if not _is_safe_public_url(url):
        return ""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": _BROWSER_UA, "Accept": "text/html"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if "html" not in resp.headers.get("Content-Type", ""):
                return ""
            data = resp.read(500_000).decode("utf-8", errors="ignore")
    except Exception:
        return ""
    for pattern in _OG_IMAGE_PATTERNS:
        match = re.search(pattern, data, re.IGNORECASE)
        if match:
            # Meta content is HTML-escaped (e.g. &#x2f; for "/"); decode it.
            return html.unescape(match.group(1))[:1000]
    return ""


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
