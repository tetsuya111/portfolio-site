import pytest

from app.batch.urls import TOP_URL, InvalidChartUrl, resolve_chart_url

HOT = "https://billboard.mryogaku.com/php/dispHot100.php?date=2025-11-15"


@pytest.mark.parametrize(
    "url",
    [
        "https://billboard.mryogaku.com/",
        "https://billboard.mryogaku.com",
        "https://billboard.mryogaku.com/#google_vignette",
        "https://billboard.mryogaku.com/index.php",
        "https://billboard.mryogaku.com/s/",
        "  https://billboard.mryogaku.com/  ",
    ],
)
def test_top_page_variants(url):
    target = resolve_chart_url(url)
    assert target.kind == "top"
    assert target.url == TOP_URL


@pytest.mark.parametrize(
    "url",
    [
        "https://billboard.mryogaku.com/php/chart.php?date=2025-11-15",
        "https://billboard.mryogaku.com/php/dispHot100.php?date=2025-11-15",
        "https://billboard.mryogaku.com/s/php/chart.php?date=2025-11-15",
        "https://billboard.mryogaku.com/s/php/dispHot100.php?date=2025-11-15#x",
        "http://billboard.mryogaku.com/php/chart.php?date=2025-11-15",
        "https://BILLBOARD.mryogaku.com/php/chart.php?date=2025-11-15&foo=1",
    ],
)
def test_chart_php_normalized(url):
    target = resolve_chart_url(url)
    assert target.kind == "hot100"
    assert target.url == HOT


@pytest.mark.parametrize(
    "url",
    [
        "https://billboard.mryogaku.com/php/chart.php?date=2025-1-5",
        "https://billboard.mryogaku.com/php/chart.php?date=x",
        "https://billboard.mryogaku.com/php/chart.php",
        "https://billboard.mryogaku.com/php/chart.php?date=2025-13-40",
        "https://billboard.mryogaku.com/php/artist.php?artist=Taylor",
    ],
)
def test_rejects_bad_date_or_path(url):
    with pytest.raises(InvalidChartUrl):
        resolve_chart_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/php/chart.php?date=2025-11-15",
        "https://billboard.mryogaku.com.evil.example/",
        "https://evil.example/billboard.mryogaku.com/",
        "https://user@billboard.mryogaku.com/",
        "https://billboard.mryogaku.com:8443/",
        "ftp://billboard.mryogaku.com/",
        "javascript:alert(1)",
        "",
        "https://billboard.mryogaku.com/" + "a" * 2100,
    ],
)
def test_rejects_lookalike_hosts(url):
    with pytest.raises(InvalidChartUrl):
        resolve_chart_url(url)
