from datetime import date

import pytest
from django.db import IntegrityError, transaction

from catalog.models import Event, FetchedPage

pytestmark = pytest.mark.django_db


def test_event_end_before_start_violates_constraint():
    with pytest.raises(IntegrityError), transaction.atomic():
        Event.objects.create(
            name="逆転イベント", start_date=date(2026, 12, 6), end_date=date(2026, 12, 5)
        )


def test_fetched_page_url_unique():
    FetchedPage.objects.create(url="https://example.com/a", kind="event", status_code=200)
    with pytest.raises(IntegrityError), transaction.atomic():
        FetchedPage.objects.create(url="https://example.com/a", kind="event", status_code=200)


@pytest.mark.parametrize(
    ("status", "expected"), [(200, True), (299, True), (404, False), (None, False)]
)
def test_fetched_page_is_success(status, expected):
    page = FetchedPage(url="https://example.com/", kind="event", status_code=status)

    assert page.is_success is expected
