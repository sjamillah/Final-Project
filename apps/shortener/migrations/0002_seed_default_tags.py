from django.db import migrations, models  # type: ignore[reportMissingImports]

DEFAULT_TAGS = ["Marketing", "Social", "Work", "Personal"]


def seed_tags(apps, schema_editor):
    Tag = apps.get_model("shortener", "Tag")
    for name in DEFAULT_TAGS:
        Tag.objects.get_or_create(name=name)


def reverse_seed_tags(apps, schema_editor):
    Tag = apps.get_model("shortener", "Tag")
    Tag.objects.filter(name__in=DEFAULT_TAGS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("shortener", "0001_initial"),
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
            options={
                "db_table": "tags",
            },
        ),
        migrations.RunPython(seed_tags, reverse_code=reverse_seed_tags),
    ]
