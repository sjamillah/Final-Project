import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50, unique=True)),
            ],
            options={"db_table": "tags"},
        ),
        migrations.CreateModel(
            name="URL",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("original_url", models.URLField(max_length=2048)),
                ("short_code", models.CharField(max_length=10, unique=True)),
                (
                    "custom_alias",
                    models.CharField(blank=True, max_length=50, null=True, unique=True),
                ),
                (
                    "title",
                    models.CharField(
                        blank=True, max_length=255, null=True, unique=True
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        blank=True, max_length=255, null=True, unique=True
                    ),
                ),
                (
                    "favicon",
                    models.CharField(
                        blank=True, max_length=2048, null=True, unique=True
                    ),
                ),
                ("click_count", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="urls",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tags",
                    models.ManyToManyField(
                        blank=True, related_name="urls", to="shortener.tag"
                    ),
                ),
            ],
            options={"db_table": "urls"},
        ),
        migrations.CreateModel(
            name="Click",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True, null=True)),
                ("country", models.CharField(blank=True, max_length=100, null=True)),
                ("city", models.CharField(blank=True, max_length=100, null=True)),
                ("referrer", models.URLField(blank=True, max_length=2048, null=True)),
                ("clicked_at", models.DateTimeField(auto_now_add=True)),
                (
                    "url",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="clicks",
                        to="shortener.url",
                    ),
                ),
            ],
            options={"db_table": "clicks"},
        ),
        migrations.AddConstraint(
            model_name="url",
            constraint=models.UniqueConstraint(
                fields=("owner", "original_url"),
                name="uniq_owner_original_url",
            ),
        ),
        migrations.AddConstraint(
            model_name="url",
            constraint=models.UniqueConstraint(
                condition=models.Q(owner__isnull=True),
                fields=("original_url",),
                name="uniq_anon_original_url",
            ),
        ),
        migrations.AddIndex(
            model_name="url",
            index=models.Index(fields=["created_at"], name="urls_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="url",
            index=models.Index(fields=["click_count"], name="urls_click_count_idx"),
        ),
        migrations.AddIndex(
            model_name="url",
            index=models.Index(
                fields=["is_active", "expires_at"], name="urls_is_active_expires_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="url",
            index=models.Index(
                fields=["owner", "created_at"], name="urls_owner_created_at_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="click",
            index=models.Index(
                fields=["url", "clicked_at"], name="clicks_url_clicked_at_idx"
            ),
        ),
    ]
