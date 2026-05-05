import pytest
from apps.shortener.models import Tag

DEFAULT_TAGS = ["Marketing", "Social", "Work", "Personal"]


@pytest.mark.django_db
class TestSeedMigration:

    def test_default_tags_exist(self):
        for name in DEFAULT_TAGS:
            assert Tag.objects.filter(
                name=name
            ).exists(), f"Expected tag '{name}' to exist after migration"

    def test_no_duplicate_tags(self):
        for name in DEFAULT_TAGS:
            count = Tag.objects.filter(name=name).count()
            assert count == 1, f"Expected exactly 1 tag named '{name}', found {count}"

    def test_all_four_default_tags_present(self):
        seeded = Tag.objects.filter(name__in=DEFAULT_TAGS).count()
        assert seeded == len(DEFAULT_TAGS)
