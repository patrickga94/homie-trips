from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.generic import View


class SpaFallbackView(View):
    """Serve the compiled SPA's index.html for any non-API client-side route.

    WhiteNoise serves the SPA's static assets at the site root in production;
    this catch-all returns index.html so Vue Router can handle deep links.
    In local dev the SPA is served by Vite, so this is only hit if someone
    opens the Django server directly without a build present.
    """

    def get(self, request, *args, **kwargs):
        index = settings.SPA_DIR / "index.html"
        if index.exists():
            return HttpResponse(index.read_text(encoding="utf-8"))
        return HttpResponse(
            "Frontend build not found. In development, open the Vite dev server "
            "(http://localhost:5173). In production, build the SPA into backend/spa/.",
            content_type="text/plain",
            status=200,
        )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("trips.urls")),
    # Client-side routes fall through to the SPA (excluding api/ and admin/).
    re_path(r"^(?!api/|admin/|static/).*$", SpaFallbackView.as_view()),
]
