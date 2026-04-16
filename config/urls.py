from django.urls import path, include
from apps.api.v1.views import URLRedirectView

urlpatterns = [
    path("api/v1/", include("apps.api.v1.urls")),
    path("<str:short_code>/", URLRedirectView.as_view(), name="url-redirect"),
]
