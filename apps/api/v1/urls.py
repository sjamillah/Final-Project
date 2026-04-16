from django.urls import path
from .views import URLCreateView

urlpatterns = [
    path("urls/", URLCreateView.as_view(), name="url-create"),
]
