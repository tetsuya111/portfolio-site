import datetime as dt

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from events.models import Event, EventSource, FetchedPage

pytestmark = pytest.mark.django_db


def test_normalized_title_is_computed_on_save():
    e = Event.objects.create(title="【サイン会】 ＡＢＣ 発売記念", start_date=dt.date(2026, 12, 1))
    assert e.normalized_title == "サイン会abc発売記念"


def test_end_date_defaults_to_start_date():
    e = Event.objects.create(title="x", start_date=dt.date(2026, 12, 1))
    assert e.end_date == dt.date(2026, 12, 1)


def test_end_date_before_start_date_is_invalid():
    e = Event(title="x", start_date=dt.date(2026, 12, 2), end_date=dt.date(2026, 12, 1))
    with pytest.raises(ValidationError):
        e.full_clean()


def test_event_source_url_is_unique():
    e = Event.objects.create(title="x", start_date=dt.date(2026, 12, 1))
    EventSource.objects.create(event=e, source_name="a", source_url="https://example.com/1")
    with pytest.raises(IntegrityError):
        EventSource.objects.create(event=e, source_name="b", source_url="https://example.com/1")


def test_fetched_page_url_is_unique():
    FetchedPage.objects.create(url="https://example.com/", source_name="a", kind="list")
    with pytest.raises(IntegrityError):
        FetchedPage.objects.create(url="https://example.com/", source_name="a", kind="list")
