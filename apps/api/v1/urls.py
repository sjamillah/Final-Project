from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .auth_views import LoginView, LogoutView, RegisterView
from .url_views import URLAnalyticsView, URLCreateView, URLDetailView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("urls/", URLCreateView.as_view(), name="url-list-create"),
    path("urls/<str:short_code>/", URLDetailView.as_view(), name="url-detail"),
    path(
        "urls/<str:short_code>/analytics/",
        URLAnalyticsView.as_view(),
        name="url-analytics",
    ),
]
