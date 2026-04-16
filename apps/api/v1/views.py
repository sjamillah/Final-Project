from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import redirect

from apps.shortener.services import create_short_url, get_url_by_code
from .serializers import URLCreateSerializer, URLResponseSerializer


class URLCreateView(APIView):

    def post(self, request: Request) -> Response:
        serializer = URLCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = create_short_url(serializer.validated_data["original_url"])
        response = URLResponseSerializer(url)

        return Response(response.data, status=status.HTTP_201_CREATED)


class URLRedirectView(APIView):

    def get(self, request: Request, short_code: str) -> Response:
        url = get_url_by_code(short_code)

        if not url:
            return Response(
                {"detail": "Short code not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return redirect(url.original_url)
