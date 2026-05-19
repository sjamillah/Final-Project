from django.urls import path

from .views import PreviewView

urlpatterns = [
    path("api/preview/", PreviewView.as_view(), name="preview"),
]
