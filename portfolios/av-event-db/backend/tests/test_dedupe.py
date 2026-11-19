import datetime as dt

import pytest

from events.crawler.dedupe import (
    SIMILARITY_THRESHOLD,
    find_duplicate,
    levenshtein,
    normalize_title,
    similarity,
)
from events.models import Event, EventSource


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [("kitten", "sitting", 3), ("", "abc", 3), ("abc", "", 3), ("", "", 0), ("同じ", "同じ", 0)],
)
def test_levenshtein(a, b, expected):
    assert levenshtein(a, b) == expected


def test_similarity():
    assert similarity("", "") == 1.0
    assert similarity("abcd", "abcf") == pytest.approx(0.75)


def test_normalize_title_removes_brackets_spaces_and_width():
    assert normalize_title(" 【サイン会】ＡＢＣ  発売記念！ ") == "サイン会abc発売記念"


def test_threshold_boundary():
    # 10文字中2文字違い（0.8）は同一、3文字違い（0.7）は別
    assert similarity("abcdefghij", "abcdefghxy") >= SIMILARITY_THRESHOLD
    assert similarity("abcdefghij", "abcdefgxyz") < SIMILARITY_THRESHOLD


@pytest.mark.django_db
class TestFindDuplicate:
    def _event(self, title, day=1):
        return Event.objects.create(title=title, start_date=dt.date(2026, 12, day))

    def test_similar_title_on_same_day(self):
        e = self._event("新作DVD発売記念サイン会 in 秋葉原")
        found = find_duplicate("【新作DVD発売記念】サイン会in秋葉原", dt.date(2026, 12, 1), None)
        assert found == e

    def test_different_day_is_not_duplicate(self):
        self._event("新作DVD発売記念サイン会 in 秋葉原")
        assert find_duplicate("新作DVD発売記念サイン会 in 秋葉原", dt.date(2026, 12, 2), None) is None

    def test_dissimilar_title_is_not_duplicate(self):
        self._event("新作DVD発売記念サイン会")
        assert find_duplicate("トークライブ 第2部", dt.date(2026, 12, 1), None) is None

    def test_same_source_url_wins(self):
        e = self._event("まったく別のタイトル", day=5)
        EventSource.objects.create(event=e, source_name="s", source_url="https://example.com/e/1")
        found = find_duplicate("タイトル変更後", dt.date(2026, 12, 6), "https://example.com/e/1")
        assert found == e

    def test_most_similar_is_chosen(self):
        self._event("サイン会 秋葉原 第1部")
        best = self._event("サイン会 秋葉原 第2部")
        found = find_duplicate("サイン会 秋葉原 第2部!", dt.date(2026, 12, 1), None)
        assert found == best
