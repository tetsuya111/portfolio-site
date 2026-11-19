import json
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from catalog.collector.normalizer import (
    PREFECTURES,
    ClaudeNormalizer,
    NormalizedLocation,
    RuleBasedNormalizer,
    get_normalizer,
)

rule = RuleBasedNormalizer()


def test_prefectures_has_47():
    assert len(PREFECTURES) == 47


def test_known_venue_is_normalized():
    result = rule.normalize("東京ビッグサイト　西1ホール")

    assert result.venue_name == "東京ビッグサイト"
    assert result.prefecture == "東京都"
    assert result.address


def test_venue_alias_is_normalized():
    assert rule.normalize("ビッグサイト").venue_name == "東京ビッグサイト"


def test_full_width_alias_is_normalized():
    assert rule.normalize("ＩＮＴＥＸ大阪").venue_name == "インテックス大阪"


def test_prefecture_is_extracted_from_unknown_venue():
    result = rule.normalize("大阪府大阪市 某ホール（2F）")

    assert result.prefecture == "大阪府"
    assert result.venue_name == "大阪府大阪市 某ホール"


def test_empty_location():
    assert rule.normalize("   ") == NormalizedLocation("", "", "")


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def fake_client(text=None, *, stop_reason="end_turn", error=None):
    response = SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)] if text is not None else [],
    )
    return SimpleNamespace(messages=FakeMessages(response, error))


def test_claude_result_is_used():
    payload = {
        "venue_name": "幕張メッセ",
        "prefecture": "千葉県",
        "address": "千葉県千葉市美浜区中瀬2-1",
    }
    client = fake_client(json.dumps(payload, ensure_ascii=False))

    result = ClaudeNormalizer(client, fallback=rule).normalize("メッセ 9-11ホール")

    assert result == NormalizedLocation("幕張メッセ", "千葉県", "千葉県千葉市美浜区中瀬2-1")
    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert "メッセ 9-11ホール" in call["messages"][0]["content"]


@pytest.mark.parametrize(
    "client",
    [
        fake_client("not json"),
        fake_client(json.dumps({"venue_name": "x", "prefecture": "火星県", "address": ""})),
        fake_client(json.dumps({"venue_name": "x"}), stop_reason="refusal"),
        fake_client(
            error=anthropic.APIConnectionError(
                request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            )
        ),
    ],
    ids=["broken-json", "bad-prefecture", "refusal", "api-error"],
)
def test_claude_falls_back_to_rule(client):
    result = ClaudeNormalizer(client, fallback=rule).normalize("東京ビッグサイト")

    assert result == rule.normalize("東京ビッグサイト")


def test_claude_is_not_called_for_empty_location():
    client = fake_client("{}")

    ClaudeNormalizer(client, fallback=rule).normalize("")

    assert client.messages.calls == []


def test_get_normalizer_without_key_is_rule_based():
    assert isinstance(get_normalizer({}), RuleBasedNormalizer)


def test_get_normalizer_with_key_is_claude():
    normalizer = get_normalizer({"ANTHROPIC_API_KEY": "dummy", "CLAUDE_MODEL": "claude-sonnet-5-5"})

    assert isinstance(normalizer, ClaudeNormalizer)
    assert normalizer.model == "claude-sonnet-5-5"
