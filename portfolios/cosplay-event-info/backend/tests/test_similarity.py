import pytest

from catalog.collector.similarity import levenshtein, normalize_name, similarity


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("kitten", "sitting", 3),
        ("", "abc", 3),
        ("abc", "", 3),
        ("同じ", "同じ", 0),
        ("あいう", "あう", 1),
    ],
)
def test_levenshtein(a, b, expected):
    assert levenshtein(a, b) == expected


def test_normalize_name_ignores_width_case_space_and_symbols():
    assert normalize_name("Ｃｏｓ Fes！") == normalize_name("cosfes")
    assert normalize_name("コス・フェス") == normalize_name("コスフェス")


def test_similarity_identical_is_one():
    assert similarity("a", "a") == 1.0


def test_similarity_both_empty_is_zero():
    assert similarity("", "") == 0.0


def test_similarity_ignores_spacing():
    assert similarity("コスプレ博 in TFT", "コスプレ博inTFT") == 1.0


def test_similarity_ratio():
    # 10文字中1文字違い → 0.9
    assert similarity("abcdefghij", "abcdefghiX") == pytest.approx(0.9)


def test_similarity_different_names_is_low():
    assert similarity("ホココス", "となコス") < 0.85
