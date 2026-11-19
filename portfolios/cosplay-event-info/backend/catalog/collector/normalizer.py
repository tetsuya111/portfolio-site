"""開催場所の正規化（EV-4〜EV-6）。

ANTHROPIC_API_KEY があれば Claude で補完・正規化し、なければ・失敗したらルールで正規化する。
"""

import json
import logging
import os
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic

logger = logging.getLogger(__name__)

PREFECTURES: tuple[str, ...] = (
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
)  # fmt: skip

DEFAULT_CLAUDE_MODEL = "claude-opus-5-5"


@dataclass(frozen=True)
class NormalizedLocation:
    venue_name: str
    prefecture: str
    address: str


class Normalizer(Protocol):
    def normalize(self, raw: str) -> NormalizedLocation: ...


@dataclass(frozen=True)
class _KnownVenue:
    name: str
    prefecture: str
    address: str
    aliases: tuple[str, ...]


# 主要なイベント会場の辞書（別名は表記ゆれの吸収用）
KNOWN_VENUES: tuple[_KnownVenue, ...] = (
    _KnownVenue("東京ビッグサイト", "東京都", "東京都江東区有明3-11-1",
                ("東京ビッグサイト", "ビッグサイト", "東京国際展示場", "tokyo big sight")),
    _KnownVenue("幕張メッセ", "千葉県", "千葉県千葉市美浜区中瀬2-1",
                ("幕張メッセ", "makuhari messe")),
    _KnownVenue("インテックス大阪", "大阪府", "大阪府大阪市住之江区南港北1-5-102",
                ("インテックス大阪", "intex大阪", "intex osaka")),
    _KnownVenue("ポートメッセなごや", "愛知県", "愛知県名古屋市港区金城ふ頭2-2",
                ("ポートメッセなごや", "ポートメッセ名古屋")),
    _KnownVenue("サンシャインシティ", "東京都", "東京都豊島区東池袋3-1",
                ("サンシャインシティ", "池袋サンシャイン")),
    _KnownVenue("東京ドームシティ", "東京都", "東京都文京区後楽1-3-61",
                ("東京ドームシティ", "プリズムホール")),
    _KnownVenue("西日本総合展示場", "福岡県", "福岡県北九州市小倉北区浅野3-7-1",
                ("西日本総合展示場",)),
    _KnownVenue("夢メッセみやぎ", "宮城県", "宮城県仙台市宮城野区港3-1-7",
                ("夢メッセみやぎ", "夢メッセ宮城")),
)  # fmt: skip

_BRACKETS = re.compile(r"[（(【\[［].*?[）)】\]］]")
_SPACES = re.compile(r"\s+")


def _match_key(s: str) -> str:
    return _SPACES.sub("", unicodedata.normalize("NFKC", s).casefold())


def _clean(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw)
    text = _BRACKETS.sub("", text)
    return _SPACES.sub(" ", text).strip()


def find_prefecture(text: str) -> str:
    positions = [(text.find(p), p) for p in PREFECTURES if p in text]
    return min(positions)[1] if positions else ""


class RuleBasedNormalizer:
    """全角半角の統一・補足の除去・主要会場の辞書・都道府県の抽出で正規化する。"""

    def normalize(self, raw: str) -> NormalizedLocation:
        text = _clean(raw)
        if not text:
            return NormalizedLocation("", "", "")
        key = _match_key(text)
        for venue in KNOWN_VENUES:
            if any(_match_key(alias) in key for alias in venue.aliases):
                return NormalizedLocation(venue.name, venue.prefecture, venue.address)
        return NormalizedLocation(text, find_prefecture(text), "")


_SYSTEM_PROMPT = (
    "あなたは日本のイベント会場の情報を正規化するアシスタントです。"
    "与えられた開催場所の表記から、正式な会場名・都道府県・住所を答えてください。"
    "都道府県は47都道府県の正式名（例: 東京都）で答えてください。"
    "ホール番号や階数などの補足は会場名に含めないでください。"
    "分からない項目は推測せず空文字にしてください。"
)

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "venue_name": {"type": "string"},
        "prefecture": {"type": "string"},
        "address": {"type": "string"},
    },
    "required": ["venue_name", "prefecture", "address"],
    "additionalProperties": False,
}


class ClaudeNormalizer:
    """Claude の構造化出力で会場情報を補完する。失敗時は fallback の結果を返す（EV-6）。"""

    def __init__(
        self, client: Any, fallback: Normalizer, model: str = DEFAULT_CLAUDE_MODEL
    ) -> None:
        self.client = client
        self.fallback = fallback
        self.model = model

    def normalize(self, raw: str) -> NormalizedLocation:
        if not _clean(raw):
            return self.fallback.normalize(raw)
        try:
            return self._ask(raw)
        except (anthropic.APIError, ValueError, KeyError, TypeError) as exc:
            logger.warning("AI による開催場所の正規化に失敗したためルールで正規化します: %s", exc)
            return self.fallback.normalize(raw)

    def _ask(self, raw: str) -> NormalizedLocation:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"開催場所の表記: {raw}"}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": _SCHEMA}},
        )
        if response.stop_reason != "end_turn":
            raise ValueError(f"想定外の stop_reason: {response.stop_reason}")
        text = next(b.text for b in response.content if b.type == "text")
        data = json.loads(text)  # 壊れた JSON は ValueError（JSONDecodeError）
        venue_name = str(data["venue_name"]).strip()
        prefecture = str(data["prefecture"]).strip()
        if not venue_name or (prefecture and prefecture not in PREFECTURES):
            raise ValueError(f"不正な正規化結果: {data!r}")
        return NormalizedLocation(venue_name, prefecture, str(data["address"]).strip())


def get_normalizer(env: Mapping[str, str] | None = None) -> Normalizer:
    """API キーがあれば ClaudeNormalizer、なければ RuleBasedNormalizer を返す（EV-5）。"""
    env = os.environ if env is None else env
    rule = RuleBasedNormalizer()
    api_key = env.get("ANTHROPIC_API_KEY")
    if not api_key:
        return rule
    client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    return ClaudeNormalizer(
        client, fallback=rule, model=env.get("CLAUDE_MODEL") or DEFAULT_CLAUDE_MODEL
    )
