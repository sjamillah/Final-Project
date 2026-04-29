import logging

from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.shortener.selectors import RedirectStatus, resolve_redirect_url
from apps.shortener.services import (
    build_click_metadata,
    create_click_for_url,
    create_short_url,
)
from .serializers import URLCreateSerializer, URLResponseSerializer

logger = logging.getLogger(__name__)


class URLCreateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        request=URLCreateSerializer,
        responses={201: URLResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = URLCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = create_short_url(serializer.validated_data["original_url"])
        response = URLResponseSerializer(url)

        return Response(response.data, status=status.HTTP_201_CREATED)


class URLRedirectView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="short_code",
                type=str,
                location=OpenApiParameter.PATH,
                required=True,
                description="Short code generated for a URL.",
            )
        ],
        responses={302: None, 404: None, 410: None},
    )
    def get(self, request: Request, short_code: str) -> HttpResponse:
        resolution = resolve_redirect_url(short_code)
        state = resolution.status
        url = resolution.url

        if state in {RedirectStatus.NOT_FOUND, RedirectStatus.INACTIVE}:
            logger.info("redirect_not_found", extra={"short_code": short_code})
            return Response(
                {"detail": "Short code not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if state == RedirectStatus.EXPIRED:
            logger.info("redirect_expired", extra={"short_code": short_code})
            return Response(
                {"detail": "Short code has expired."},
                status=status.HTTP_410_GONE,
            )

        try:
            create_click_for_url(url=url, metadata=build_click_metadata(request.META))
        except Exception:
            logger.exception(
                "redirect_click_tracking_failed",
                extra={"short_code": short_code, "url_id": url.pk},
            )

        return redirect(url.original_url)
