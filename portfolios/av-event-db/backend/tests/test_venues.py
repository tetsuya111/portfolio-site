import json
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from events.crawler.venues import (
    ClaudeVenueNormalizer,
    GoogleGeocoder,
    NormalizedVenue,
    RuleVenueNormalizer,
    VenueResolver,
    build_default_resolver,
    preprocess,
)
from events.models import Venue, VenueAlias


class FakeNormalizer:
    def __init__(self, result=None):
        self.calls: list[str] = []
        self.result = result

    def normalize(self, text):
        self.calls.append(text)
        return self.result or NormalizedVenue(
            name="秋葉原ホール", address="東京都千代田区外神田1-1", prefecture="東京都"
        )


class FakeGeocoder:
    def __init__(self, result=(35.7, 139.77)):
        self.calls: list[str] = []
        self.result = result

    def geocode(self, query):
        self.calls.append(query)
        return self.result


def test_preprocess():
    assert preprocess("  ＡＢＣホール　\n 3F ") == "ABCホール 3F"


def test_rule_normalizer_extracts_prefecture():
    v = RuleVenueNormalizer().normalize("大阪府大阪市 なんばホール")
    assert v == NormalizedVenue(name="大阪府大阪市 なんばホール", address="", prefecture="大阪府")


def test_rule_normalizer_without_prefecture():
    assert RuleVenueNormalizer().normalize("オンライン").prefecture == ""


@pytest.mark.django_db
class TestResolver:
    def test_creates_venue_and_alias_and_geocodes(self):
        geo = FakeGeocoder()
        venue = VenueResolver(FakeNormalizer(), geo).resolve(" 秋葉原ホール（東京） ")
        assert venue.name == "秋葉原ホール"
        assert venue.prefecture == "東京都"
        assert (venue.latitude, venue.longitude) == (35.7, 139.77)
        assert geo.calls == ["秋葉原ホール 東京都千代田区外神田1-1"]
        assert VenueAlias.objects.get().raw_text == "秋葉原ホール(東京)"

    def test_alias_skips_normalizer(self):
        norm = FakeNormalizer()
        resolver = VenueResolver(norm, None)
        first = resolver.resolve("秋葉原ホール")
        second = resolver.resolve("秋葉原ホール ")
        assert first == second
        assert len(norm.calls) == 1

    def test_reuses_venue_with_same_name_and_address(self):
        norm = FakeNormalizer()
        resolver = VenueResolver(norm, None)
        a = resolver.resolve("秋葉原ホール")
        b = resolver.resolve("秋葉原ホール 東京")
        assert a == b
        assert Venue.objects.count() == 1
        assert VenueAlias.objects.count() == 2

    def test_empty_text_returns_none(self):
        assert VenueResolver(FakeNormalizer(), None).resolve("  ") is None

    def test_geocode_failure_still_saves(self):
        venue = VenueResolver(FakeNormalizer(), FakeGeocoder(result=None)).resolve("x")
        assert venue.latitude is None
        assert Venue.objects.count() == 1

    def test_default_resolver_without_keys_uses_rules(self, settings):
        settings.ANTHROPIC_API_KEY = ""
        settings.GOOGLE_MAPS_GEOCODING_API_KEY = ""
        resolver = build_default_resolver()
        assert isinstance(resolver.normalizer, RuleVenueNormalizer)
        assert resolver.geocoder is None


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


def fake_client(messages):
    return SimpleNamespace(beta=SimpleNamespace(messages=messages))


def response(text, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)]
    )


def test_claude_normalizer_parses_json():
    payload = {"name": "秋葉原ホール", "address": "東京都千代田区外神田1-1", "prefecture": "東京都"}
    messages = FakeMessages(response(json.dumps(payload, ensure_ascii=False)))
    v = ClaudeVenueNormalizer(fake_client(messages), "claude-opus-5-5").normalize("秋葉原ホール")
    assert v == NormalizedVenue(**payload)
    assert messages.kwargs["model"] == "claude-opus-5-5"
    assert messages.kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "秋葉原ホール" in messages.kwargs["messages"][0]["content"]


def test_claude_normalizer_rejects_unknown_prefecture():
    payload = {"name": "ホール", "address": "", "prefecture": "東京"}
    messages = FakeMessages(response(json.dumps(payload)))
    v = ClaudeVenueNormalizer(fake_client(messages), "m").normalize("東京都 ホール")
    assert v.prefecture == "東京都"


@pytest.mark.parametrize(
    "messages",
    [
        FakeMessages(response("not json")),
        FakeMessages(response('{"name": ""}')),
        FakeMessages(response("{}", stop_reason="refusal")),
        FakeMessages(
            error=anthropic.APIConnectionError(request=httpx.Request("POST", "https://x"))
        ),
    ],
)
def test_claude_normalizer_falls_back_to_rules(messages):
    v = ClaudeVenueNormalizer(fake_client(messages), "m").normalize("大阪府 なんばホール")
    assert v == NormalizedVenue(name="大阪府 なんばホール", address="", prefecture="大阪府")


def geocoder(handler):
    return GoogleGeocoder("key", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_geocoder_success():
    def handler(request):
        assert request.url.params["address"] == "秋葉原ホール"
        assert request.url.params["key"] == "key"
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "results": [{"geometry": {"location": {"lat": 1.5, "lng": 2.5}}}],
            },
        )

    assert geocoder(handler).geocode("秋葉原ホール") == (1.5, 2.5)


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(200, json={"status": "ZERO_RESULTS", "results": []}),
        lambda r: httpx.Response(500),
        lambda r: httpx.Response(200, text="oops"),
    ],
)
def test_geocoder_failure_returns_none(handler):
    assert geocoder(handler).geocode("x") is None
