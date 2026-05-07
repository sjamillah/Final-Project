from django.db import migrations

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
        migrations.RunPython(seed_tags, reverse_code=reverse_seed_tags),
    ]
