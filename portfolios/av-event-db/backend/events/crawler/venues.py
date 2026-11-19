"""開催場所の補完・正規化（AI／規則ベース）とジオコーディング（REQ-4）。"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic
import httpx
from django.conf import settings
from django.db import transaction

from events.models import Venue, VenueAlias

logger = logging.getLogger(__name__)

PREFECTURES = (
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
)  # fmt: skip
_SPACES = re.compile(r"\s+")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def preprocess(text: str) -> str:
    """NFKC・空白の統一・前後の空白除去。"""
    return _SPACES.sub(" ", unicodedata.normalize("NFKC", text or "")).strip()


def extract_prefecture(text: str) -> str:
    for pref in PREFECTURES:
        if pref in text:
            return pref
    return ""


@dataclass(frozen=True)
class NormalizedVenue:
    name: str
    address: str
    prefecture: str


class VenueNormalizer(Protocol):
    def normalize(self, text: str) -> NormalizedVenue: ...


class Geocoder(Protocol):
    def geocode(self, query: str) -> tuple[float, float] | None: ...


class RuleVenueNormalizer:
    def normalize(self, text: str) -> NormalizedVenue:
        text = preprocess(text)
        return NormalizedVenue(name=text[:200], address="", prefecture=extract_prefecture(text))


_SYSTEM_PROMPT = (
    "あなたは日本のイベント会場の表記を正規化するアシスタントです。"
    "与えられた開催場所の文字列から、会場の正式名称・住所・都道府県を推定してください。"
    "会場名には階数や部屋番号などの補足を含めず、建物・施設の名称だけを入れてください。"
    "住所や都道府県が分からない場合は空文字にしてください。推測で架空の住所を作らないでください。"
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "address": {"type": "string"},
        "prefecture": {"type": "string"},
    },
    "required": ["name", "address", "prefecture"],
    "additionalProperties": False,
}


class ClaudeVenueNormalizer:
    """Claude API で会場名・住所・都道府県を補完する。失敗時は規則ベースに戻す（REQ-4.3）。"""

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model
        self._fallback = RuleVenueNormalizer()

    def normalize(self, text: str) -> NormalizedVenue:
        text = preprocess(text)
        try:
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=1024,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": _SCHEMA},
                },
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"開催場所: {text}"}],
            )
        except anthropic.APIError as exc:
            logger.warning("会場の正規化APIに失敗しました: %s", exc)
            return self._fallback.normalize(text)
        if response.stop_reason == "refusal":
            return self._fallback.normalize(text)
        body = next((b.text for b in response.content if b.type == "text"), "")
        try:
            data = json.loads(body)
            name = preprocess(str(data["name"]))
            address = preprocess(str(data["address"]))
            prefecture = preprocess(str(data["prefecture"]))
        except (ValueError, KeyError, TypeError):
            return self._fallback.normalize(text)
        if not name:
            return self._fallback.normalize(text)
        if prefecture not in PREFECTURES:
            prefecture = extract_prefecture(f"{address} {text}")
        return NormalizedVenue(name=name[:200], address=address[:300], prefecture=prefecture)


class GoogleGeocoder:
    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=10.0)

    def geocode(self, query: str) -> tuple[float, float] | None:
        try:
            res = self._client.get(
                GEOCODE_URL,
                params={"address": query, "key": self._api_key, "language": "ja", "region": "jp"},
            )
            res.raise_for_status()
            data = res.json()
            if data.get("status") != "OK" or not data.get("results"):
                return None
            loc = data["results"][0]["geometry"]["location"]
            return float(loc["lat"]), float(loc["lng"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("ジオコーディングに失敗しました: %s", exc)
            return None


class VenueResolver:
    def __init__(self, normalizer: VenueNormalizer, geocoder: Geocoder | None) -> None:
        self.normalizer = normalizer
        self.geocoder = geocoder

    def resolve(self, raw_text: str) -> Venue | None:
        text = preprocess(raw_text)[:300]
        if not text:
            return None
        alias = VenueAlias.objects.select_related("venue").filter(raw_text=text).first()
        if alias:
            return alias.venue
        normalized = self.normalizer.normalize(text)
        with transaction.atomic():
            venue, created = Venue.objects.get_or_create(
                name=normalized.name,
                address=normalized.address,
                defaults={"prefecture": normalized.prefecture},
            )
            VenueAlias.objects.get_or_create(raw_text=text, defaults={"venue": venue})
        if created and self.geocoder is not None:
            coords = self.geocoder.geocode(f"{venue.name} {venue.address}".strip())
            if coords:
                venue.latitude, venue.longitude = coords
                venue.save(update_fields=["latitude", "longitude"])
        return venue


def build_default_resolver() -> VenueResolver:
    """環境変数のキーの有無に応じてノーマライザ・ジオコーダを選ぶ。"""
    if settings.ANTHROPIC_API_KEY:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        normalizer: VenueNormalizer = ClaudeVenueNormalizer(client, settings.VENUE_NORMALIZER_MODEL)
    else:
        normalizer = RuleVenueNormalizer()
    key = settings.GOOGLE_MAPS_GEOCODING_API_KEY
    return VenueResolver(normalizer, GoogleGeocoder(key) if key else None)
