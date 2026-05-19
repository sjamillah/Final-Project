from rest_framework import serializers

from apps.shortener.models import Tag, URL


def validate_custom_alias_uniqueness(value, exclude_pk=None):
    if not value:
        return value

    qs = URL.objects.filter(custom_alias=value) | URL.objects.filter(short_code=value)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        raise serializers.ValidationError("This custom alias is already taken.")

    if not value.replace("-", "").replace("_", "").isalnum():
        raise serializers.ValidationError(
            "Custom alias can only contain letters, numbers, hyphens, and underscores."
        )
    return value


class URLCreateSerializer(serializers.Serializer):
    original_url = serializers.URLField(max_length=2048)
    custom_alias = serializers.CharField(
        max_length=50,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    title = serializers.CharField(
        max_length=255,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
    )

    def validate_custom_alias(self, value):
        return validate_custom_alias_uniqueness(value)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class URLResponseSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    owner_username = serializers.CharField(
        source="owner.username",
        read_only=True,
        allow_null=True,
    )
    short_url = serializers.SerializerMethodField()

    class Meta:
        model = URL
        fields = [
            "id",
            "original_url",
            "short_code",
            "custom_alias",
            "short_url",
            "title",
            "description",
            "favicon",
            "click_count",
            "is_active",
            "expires_at",
            "tags",
            "owner_username",
            "created_at",
        ]
        read_only_fields = fields

    def get_short_url(self, obj):
        request = self.context.get("request")
        code = obj.custom_alias or obj.short_code
        if request:
            return request.build_absolute_uri(f"/{code}/")
        return f"/{code}/"


class URLUpdateSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
    )

    class Meta:
        model = URL
        fields = [
            "original_url",
            "custom_alias",
            "title",
            "is_active",
            "expires_at",
            "tags",
        ]

    def validate_custom_alias(self, value):
        return validate_custom_alias_uniqueness(value, exclude_pk=self.instance.pk)
