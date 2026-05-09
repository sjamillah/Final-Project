import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: None, 503: None})
    def get(self, request):
        checks: dict[str, str] = {}

        # Database check
        try:
            from django.db import connection

            connection.ensure_connection()
            checks["db"] = "ok"
        except Exception:
            logger.exception("health_check_db_failed")
            checks["db"] = "error"

        # Redis check
        try:
            from django.core.cache import cache

            cache.set("_health", "1", timeout=5)
            checks["redis"] = "ok"
        except Exception:
            logger.exception("health_check_redis_failed")
            checks["redis"] = "error"

        all_ok = all(v == "ok" for v in checks.values())
        return Response(
            {
                "status": "ok" if all_ok else "degraded",
                "checks": checks,
            },
            status=(
                status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
            ),
        )
