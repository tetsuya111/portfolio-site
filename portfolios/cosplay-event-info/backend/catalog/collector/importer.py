"""抽出した項目を DB に取り込む。似た名前のものは既存のレコードに統合する（EV-3・CP-3）。"""

import math

from django.conf import settings
from django.db import transaction

from catalog.collector.normalizer import Normalizer
from catalog.collector.parsers import is_http_url
from catalog.collector.parsers.cosplayers import CosplayerItem
from catalog.collector.parsers.events import EventItem
from catalog.collector.similarity import normalize_name, similarity
from catalog.models import Cosplayer, Event, FetchedPage, Venue


def _safe_url(url: str) -> str:
    return url if is_http_url(url) else ""


# ---- 会場 ----


def resolve_venue(location_raw: str, normalizer: Normalizer) -> Venue | None:
    """開催場所の表記から会場を決める。同じ表記のイベントがあればその会場を使い、正規化を省く。"""
    raw = location_raw.strip()
    if not raw:
        return None
    known = (
        Event.objects.filter(location_raw=raw, venue__isnull=False).select_related("venue").first()
    )
    if known:
        return known.venue

    location = normalizer.normalize(raw)
    if not location.venue_name:
        return None
    venue, created = Venue.objects.get_or_create(
        name=location.venue_name[:200],
        defaults={"prefecture": location.prefecture, "address": location.address[:300]},
    )
    if not created:
        changed = False
        if not venue.prefecture and location.prefecture:
            venue.prefecture, changed = location.prefecture, True
        if not venue.address and location.address:
            venue.address, changed = location.address[:300], True
        if changed:
            venue.save(update_fields=["prefecture", "address"])
    return venue


# ---- イベント ----


def _find_similar_event(item: EventItem, venue: Venue | None) -> Event | None:
    """同じ開始日で名前が似ているイベントを探す。

    開催地の都道府県がどちらも分かっていて異なる場合（「東京会場」と「大阪会場」など）は別とする。
    会場名は正規化の表記ゆれで別レコードになりうるため、会場名の違いだけでは別としない。
    """
    threshold = settings.EVENT_SIMILARITY_THRESHOLD
    prefecture = venue.prefecture if venue else ""
    best, best_score = None, 0.0
    for candidate in Event.objects.filter(start_date=item.start_date).select_related("venue"):
        other = candidate.venue.prefecture if candidate.venue else ""
        if prefecture and other and prefecture != other:
            continue
        score = similarity(candidate.name, item.name)
        if score >= threshold and score > best_score:
            best, best_score = candidate, score
    return best


@transaction.atomic
def import_event(item: EventItem, page: FetchedPage, normalizer: Normalizer) -> tuple[Event, bool]:
    """イベントを取り込み、(イベント, 新規作成なら True) を返す。"""
    end_date = max(item.start_date, item.end_date)
    venue = resolve_venue(item.location, normalizer)
    existing = _find_similar_event(item, venue)
    if existing:
        fields = []
        for name, value in (
            ("url", _safe_url(item.url)),
            ("location_raw", item.location.strip()[:300]),
            ("notes", item.notes),
            ("source_url", _safe_url(page.url)),
        ):
            if not getattr(existing, name) and value:
                setattr(existing, name, value)
                fields.append(name)
        if existing.venue_id is None and venue:
            existing.venue = venue
            fields.append("venue")
        if fields:
            existing.save(update_fields=[*fields, "updated_at"])
        existing.sources.add(page)
        return existing, False

    event = Event.objects.create(
        name=item.name[:300],
        url=_safe_url(item.url),
        location_raw=item.location.strip()[:300],
        venue=venue,
        start_date=item.start_date,
        end_date=end_date,
        notes=item.notes,
        source_url=_safe_url(page.url),
    )
    event.sources.add(page)
    return event, True


# ---- コスプレイヤー ----


def _find_similar_cosplayer(name: str) -> Cosplayer | None:
    threshold = settings.COSPLAYER_SIMILARITY_THRESHOLD
    target = normalize_name(name)
    best, best_score = None, 0.0
    for candidate in Cosplayer.objects.only("id", "name"):
        other = normalize_name(candidate.name)
        # 距離は文字数の差以上になるため、しきい値に届かない候補は計算を省く
        longest = max(len(target), len(other))
        if abs(len(target) - len(other)) > math.floor(longest * (1 - threshold) + 1e-9):
            continue
        score = similarity(candidate.name, name)
        if score >= threshold and score > best_score:
            best, best_score = candidate, score
    return Cosplayer.objects.get(pk=best.pk) if best else None


@transaction.atomic
def import_cosplayer(item: CosplayerItem, page: FetchedPage) -> tuple[Cosplayer, bool]:
    """コスプレイヤーを取り込み、(コスプレイヤー, 新規作成なら True) を返す。"""
    sns_links = list(dict.fromkeys(u for u in item.sns_links if is_http_url(u)))
    existing = _find_similar_cosplayer(item.name)
    if existing:
        for name in ("career", "description", "notes"):
            if not getattr(existing, name) and getattr(item, name):
                setattr(existing, name, getattr(item, name))
        if not existing.source_url:
            existing.source_url = _safe_url(page.url)
        existing.sns_links = list(dict.fromkeys([*existing.sns_links, *sns_links]))
        existing.save()
        existing.sources.add(page)
        return existing, False

    person = Cosplayer.objects.create(
        name=item.name[:200],
        sns_links=sns_links,
        career=item.career,
        description=item.description,
        notes=item.notes,
        source_url=_safe_url(page.url),
    )
    person.sources.add(page)
    return person, True
