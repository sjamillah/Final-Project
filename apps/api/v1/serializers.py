from rest_framework import serializers
from apps.shortener.models import URL


class URLCreateSerializer(serializers.Serializer):
    original_url = serializers.URLField(max_length=2048)


class URLResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = URL
        fields = ["short_code", "original_url", "created_at"]
