import logging

from django.shortcuts import redirect
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from apps.shortener.services import create_short_url, get_url_by_code
from .serializers import URLCreateSerializer, URLResponseSerializer

logger = logging.getLogger(__name__)


class URLCreateView(APIView):

    @extend_schema(
        request=URLCreateSerializer,
        responses={201: URLResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = URLCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = create_short_url(serializer.validated_data["original_url"])
        logger.info(
            "Created short URL for %s", serializer.validated_data["original_url"]
        )
        response = URLResponseSerializer(url)

        return Response(response.data, status=status.HTTP_201_CREATED)


class URLRedirectView(APIView):

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
    def get(self, request: Request, short_code: str) -> Response:
        url = get_url_by_code(short_code)

        if not url:
            logger.warning("Short code not found: %s", short_code)
            return Response(
                {"detail": "Short code not found."}, status=status.HTTP_404_NOT_FOUND
            )

        logger.info("Redirecting short code %s", short_code)
        return redirect(url.original_url)
