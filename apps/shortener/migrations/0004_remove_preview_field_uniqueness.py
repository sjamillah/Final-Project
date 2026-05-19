"""
Module 9 schema fix: remove unique constraints from title, description, favicon.

Why: these fields are now auto-populated by the preview service.  Many URLs
on the same domain will share identical titles or descriptions (e.g., every
page on a site with a global "description" meta tag).  The unique constraint
would silently discard valid metadata for all but the first URL, making the
feature unreliable.

The original unique=True came from Module 5/6 when these were manual fields —
that invariant no longer holds in Module 9.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "shortener",
            "0003_rename_clicks_url_clicked_at_idx_clicks_url_id_f6448b_idx_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="url",
            name="title",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="url",
            name="description",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="url",
            name="favicon",
            field=models.CharField(blank=True, max_length=2048, null=True),
        ),
    ]
