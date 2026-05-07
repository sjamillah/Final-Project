from django.urls import include, path
from rest_framework.permissions import AllowAny
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.api.v1.links.views import URLRedirectView

urlpatterns = [
    path("api/v1/", include("apps.api.v1.urls")),
    # Make schema and docs publicly viewable so the Swagger UI displays
    # request/response schemas and example bodies without requiring auth.
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema", permission_classes=[AllowAny]
        ),
        name="swagger-ui",
    ),
    path("<str:short_code>/", URLRedirectView.as_view(), name="url-redirect"),
]
