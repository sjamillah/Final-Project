from django.urls import path
from preview_service.views import PreviewView, health

urlpatterns = [
    path("api/preview/", PreviewView.as_view(), name="preview"),
    path("health/", health, name="preview-health"),
]
