from django.urls import path

from .views import URLAnalyticsView

urlpatterns = [
    path(
        "analytics/<str:short_code>/", URLAnalyticsView.as_view(), name="url-analytics"
    ),
]
