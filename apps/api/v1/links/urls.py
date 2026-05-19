from django.urls import path

from .views import URLCreateView, URLDetailView

urlpatterns = [
    path("urls/", URLCreateView.as_view(), name="url-list-create"),
    path("urls/<str:short_code>/", URLDetailView.as_view(), name="url-detail"),
]
