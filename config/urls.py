from django.urls import path, include
from apps.api.v1.views import URLRedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/v1/", include("apps.api.v1.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("<str:short_code>/", URLRedirectView.as_view(), name="url-redirect"),
]
