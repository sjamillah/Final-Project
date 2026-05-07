import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.shortener.analytics import (
    get_click_summary_per_url,
    get_clicks_by_country,
    get_clicks_per_day,
)
from apps.api.v1.permissions import IsPremiumUser
from apps.shortener.selectors import get_url_by_code_with_owner

logger = logging.getLogger(__name__)


class URLAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsPremiumUser]

    @extend_schema(responses={200: None, 403: None, 404: None})
    def get(self, request: Request, short_code: str) -> Response:
        url = get_url_by_code_with_owner(short_code)
        if not url:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        summary = (
            get_click_summary_per_url()
            .filter(pk=url.pk)
            .values("total_clicks", "last_clicked")
            .first()
        )

        return Response(
            {
                "short_code": url.short_code,
                "total_clicks": summary["total_clicks"] if summary else 0,
                "last_clicked": summary["last_clicked"] if summary else None,
                "clicks_by_country": list(get_clicks_by_country(url)),
                "clicks_per_day": list(get_clicks_per_day(url, days=30)),
            }
        )
