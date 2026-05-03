import logging

from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.shortener.analytics import get_click_summary_per_url, get_clicks_by_country
from apps.shortener.permissions import IsOwner, IsPremiumUser
from apps.shortener.selectors import (
    RedirectStatus,
    get_url_by_code_with_owner,
    get_urls_for_user,
    resolve_redirect_url,
)
from apps.shortener.services import (
    build_click_metadata,
    create_click_for_url,
    create_short_url,
    deactivate_url,
    update_url,
)
from apps.shortener.throttles import URLCreateRateThrottle

from .url_serializers import (
    URLCreateSerializer,
    URLResponseSerializer,
    URLUpdateSerializer,
)

logger = logging.getLogger(__name__)


class URLListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [URLCreateRateThrottle]

    @extend_schema(responses={200: URLResponseSerializer})
    def get(self, request: Request) -> Response:
        urls = get_urls_for_user(request.user)
        serializer = URLResponseSerializer(
            urls, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        request=URLCreateSerializer,
        responses={201: URLResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = URLCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            url = create_short_url(
                original_url=serializer.validated_data["original_url"],
                user=request.user,
                custom_alias=serializer.validated_data.get("custom_alias"),
                title=serializer.validated_data.get("title"),
                expires_at=serializer.validated_data.get("expires_at"),
                tag_names=serializer.validated_data.get("tags", []),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        return Response(
            URLResponseSerializer(url, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class URLCreateView(URLListCreateView):
    """Backward-compatible alias for the create endpoint."""


class URLDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, short_code: str, request: Request):
        url = get_url_by_code_with_owner(short_code)
        if not url:
            return None
        self.check_object_permissions(request, url)
        return url

    @extend_schema(responses={200: URLResponseSerializer, 404: None})
    def get(self, request: Request, short_code: str) -> Response:
        url = self.get_object(short_code, request)
        if not url:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(URLResponseSerializer(url, context={"request": request}).data)

    @extend_schema(
        request=URLUpdateSerializer,
        responses={200: URLResponseSerializer, 403: None, 404: None},
    )
    def put(self, request: Request, short_code: str) -> Response:
        url = self.get_object(short_code, request)
        if not url:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = URLUpdateSerializer(url, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)

        try:
            updated = update_url(url, serializer.validated_data, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        return Response(
            URLResponseSerializer(updated, context={"request": request}).data
        )

    @extend_schema(
        request=URLUpdateSerializer,
        responses={200: URLResponseSerializer, 403: None, 404: None},
    )
    def patch(self, request: Request, short_code: str) -> Response:
        url = self.get_object(short_code, request)
        if not url:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = URLUpdateSerializer(url, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            updated = update_url(url, serializer.validated_data, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        return Response(
            URLResponseSerializer(updated, context={"request": request}).data
        )

    @extend_schema(responses={204: None, 404: None})
    def delete(self, request: Request, short_code: str) -> Response:
        url = self.get_object(short_code, request)
        if not url:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        deactivate_url(url)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
                {"detail": "Short code has expired."}, status=status.HTTP_410_GONE
            )

        try:
            create_click_for_url(url=url, metadata=build_click_metadata(request.META))
        except Exception:
            logger.exception(
                "redirect_click_tracking_failed",
                extra={"short_code": short_code, "url_id": url.pk},
            )

        return redirect(url.original_url)


class URLAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsPremiumUser]

    @extend_schema(responses={200: None, 404: None, 403: None})
    def get(self, request: Request, short_code: str) -> Response:
        url = get_url_by_code_with_owner(short_code)
        if not url:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if url.owner != request.user and request.user.tier != request.user.Tier.ADMIN:
            return Response(
                {"detail": "You do not have permission to view these analytics."},
                status=status.HTTP_403_FORBIDDEN,
            )

        country_breakdown = list(get_clicks_by_country(url))
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
                "clicks_by_country": country_breakdown,
            }
        )
