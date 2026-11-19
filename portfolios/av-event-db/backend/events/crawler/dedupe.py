"""レーベンシュタイン距離によるイベントの重複判定（REQ-3）。"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from events.models import Event

# 正規化後のタイトルの類似度がこの値以上なら同一イベントとみなす（design.md 参照）
SIMILARITY_THRESHOLD = 0.8
# 「第1部」「2部」のような部番号。番号が違えば類似度にかかわらず別イベントとする
_PART_RE = re.compile(r"(\d+)部")


def levenshtein(a: str, b: str) -> int:
    """編集距離（挿入・削除・置換をそれぞれコスト1とする）。"""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def similarity(a: str, b: str) -> float:
    """1 - 距離 / 長い方の長さ。両方空なら 1.0。"""
    longest = max(len(a), len(b))
    if longest == 0:
        return 1.0
    return 1 - levenshtein(a, b) / longest


def normalize_title(title: str) -> str:
    """NFKC・小文字化し、空白・記号・句読点を取り除く。"""
    text = unicodedata.normalize("NFKC", title).lower()
    return "".join(
        ch for ch in text if not ch.isspace() and unicodedata.category(ch)[0] not in ("P", "S")
    )


def part_numbers(normalized_title: str) -> set[str]:
    return set(_PART_RE.findall(normalized_title))


def find_duplicate(title: str, start_date: dt.date, source_url: str | None) -> Event | None:
    """取り込むイベントと同一とみなせる既存イベントを返す。"""
    from events.models import Event, EventSource

    if source_url:
        src = EventSource.objects.select_related("event").filter(source_url=source_url).first()
        if src:
            return src.event

    target = normalize_title(title)
    target_parts = part_numbers(target)
    best: tuple[float, Event] | None = None
    for event in Event.objects.filter(start_date=start_date).order_by("id"):
        parts = part_numbers(event.normalized_title)
        if target_parts and parts and target_parts != parts:
            continue
        score = similarity(target, event.normalized_title)
        if score >= SIMILARITY_THRESHOLD and (best is None or score > best[0]):
            best = (score, event)
    return best[1] if best else None
