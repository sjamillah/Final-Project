from django.urls import include, path

urlpatterns = [
    path("", include("apps.preview.urls")),
]
