import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shortener", "0002_seed_default_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="url",
            name="click_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="url",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="url",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="url",
            name="tags",
            field=models.ManyToManyField(
                blank=True, related_name="urls", to="shortener.tag"
            ),
        ),
        migrations.AddField(
            model_name="url",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="urls",
                to=settings.AUTH_USER_MODEL,
            ),
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
            options={
                "db_table": "clicks",
            },
        ),
        migrations.AddIndex(
            model_name="url",
            index=models.Index(fields=["short_code"], name="urls_short_c_484089_idx"),
        ),
        migrations.AddIndex(
            model_name="url",
            index=models.Index(fields=["owner"], name="urls_owner_i_e0a75f_idx"),
        ),
        migrations.AddIndex(
            model_name="url",
            index=models.Index(fields=["created_at"], name="urls_created_71be6f_idx"),
        ),
        migrations.AddIndex(
            model_name="url",
            index=models.Index(fields=["click_count"], name="urls_click_c_24db78_idx"),
        ),
        migrations.AddIndex(
            model_name="url",
            index=models.Index(
                fields=["is_active", "expires_at"], name="urls_is_acti_847f2f_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="url",
            index=models.Index(
                fields=["owner", "created_at"], name="urls_owner_i_bf6c03_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="click",
            index=models.Index(fields=["url"], name="clicks_url_id_d3d911_idx"),
        ),
        migrations.AddIndex(
            model_name="click",
            index=models.Index(fields=["clicked_at"], name="clicks_clicked_fa0a3b_idx"),
        ),
        migrations.AddIndex(
            model_name="click",
            index=models.Index(
                fields=["url", "clicked_at"], name="clicks_url_id_f6448b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="click",
            index=models.Index(fields=["country"], name="clicks_country_72af72_idx"),
        ),
    ]
