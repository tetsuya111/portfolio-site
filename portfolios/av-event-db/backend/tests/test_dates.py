import datetime as dt

import pytest

from events.crawler.dates import parse_event_dates

TODAY = dt.date(2026, 11, 19)


@pytest.mark.parametrize(
    "text", ["2026年12月3日（木）", "2026/12/3", "2026-12-03", "2026.12.03 開催"]
)
def test_full_dates(text):
    r = parse_event_dates(text, today=TODAY)
    assert r.start_date == dt.date(2026, 12, 3)
    assert r.end_date == dt.date(2026, 12, 3)


def test_without_year_uses_current_year():
    r = parse_event_dates("12/3(木)", today=TODAY)
    assert r.start_date == dt.date(2026, 12, 3)


def test_without_year_rolls_over_to_next_year():
    r = parse_event_dates("1月10日", today=TODAY)
    assert r.start_date == dt.date(2027, 1, 10)


def test_without_year_recent_past_stays_in_current_year():
    r = parse_event_dates("11/1", today=TODAY)
    assert r.start_date == dt.date(2026, 11, 1)


def test_range():
    r = parse_event_dates("2026年12月30日〜2027年1月2日", today=TODAY)
    assert (r.start_date, r.end_date) == (dt.date(2026, 12, 30), dt.date(2027, 1, 2))


def test_range_without_year_on_end():
    r = parse_event_dates("2026/12/30 ~ 1/2", today=TODAY)
    assert r.end_date == dt.date(2027, 1, 2)


def test_time():
    r = parse_event_dates("2026/12/3 13:30〜 / 2部 16:00〜", today=TODAY)
    assert r.start_time == dt.time(13, 30)


def test_unreadable_returns_none():
    assert parse_event_dates("近日開催", today=TODAY) is None
    assert parse_event_dates("2026/13/40", today=TODAY) is None


def test_leap_day_end_without_year():
    r = parse_event_dates("2027/12/30〜2/29", today=dt.date(2027, 11, 1))
    assert r.end_date == dt.date(2028, 2, 29)


def test_leap_day_start_without_year():
    r = parse_event_dates("2/29", today=dt.date(2027, 11, 1))
    assert r.start_date == dt.date(2028, 2, 29)


def test_second_date_without_range_separator_is_not_end_date():
    r = parse_event_dates("11/23(土) ※予約受付は11/10から", today=TODAY)
    assert (r.start_date, r.end_date) == (dt.date(2026, 11, 23), dt.date(2026, 11, 23))


def test_range_with_weekday_and_time():
    r = parse_event_dates("12/30(水) 13:00〜1/2(土)", today=TODAY)
    assert r.end_date == dt.date(2027, 1, 2)
