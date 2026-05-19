from django.urls import include, path

urlpatterns = [
    path("", include("apps.api.v1.auth.urls")),
    path("", include("apps.api.v1.links.urls")),
    path("", include("apps.api.v1.analytics.urls")),
    path("", include("apps.api.v1.health.urls")),
]
