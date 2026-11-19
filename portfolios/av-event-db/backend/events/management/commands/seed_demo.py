"""画面確認用のデモデータを投入する（実在しない架空のイベント・名前）。"""

import datetime as dt

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from events.models import Actress, Event, EventSource, Venue

DEMO_SOURCE = "demo"

VENUES = [
    ("デモ秋葉原ホール", "東京都千代田区外神田1-1-1", "東京都", 35.6984, 139.7731),
    ("デモ新宿イベントスペース", "東京都新宿区新宿3-1-1", "東京都", 35.6909, 139.7046),
    ("デモ池袋ショップ", "東京都豊島区東池袋1-1-1", "東京都", 35.7295, 139.7155),
    ("デモなんばホール", "大阪府大阪市中央区難波1-1-1", "大阪府", 34.6655, 135.5013),
    ("デモ名古屋栄スタジオ", "愛知県名古屋市中区栄3-1-1", "愛知県", 35.1681, 136.9066),
    ("デモ博多ショップ", "福岡県福岡市博多区博多駅前1-1-1", "福岡県", None, None),
]

# (日数オフセット, 期間日数, 開始時刻, タイトル, 女優, 会場番号)
EVENTS = [
    (1, 1, "13:00", "新作DVD発売記念サイン会", ["サンプル花子"], 0),
    (2, 1, "18:30", "トークライブ 第1部", ["サンプル美咲", "サンプル花子"], 1),
    (2, 1, "20:30", "トークライブ 第2部", ["サンプル美咲", "サンプル花子"], 1),
    (4, 1, "14:00", "写真集発売記念 握手会", ["サンプル彩"], 2),
    (6, 2, "12:00", "撮影会 in 大阪", ["サンプル彩", "サンプル玲奈"], 3),
    (9, 1, "15:00", "名古屋 2ショットチェキ会", ["サンプル玲奈"], 4),
    (12, 1, "13:00", "博多 サイン会", ["サンプル花子"], 5),
    (15, 1, "19:00", "ファンミーティング", ["サンプル美咲"], 0),
    (20, 3, "11:00", "ポップアップストア", ["サンプル彩", "サンプル花子"], 1),
    (28, 1, "16:00", "年末スペシャルイベント", ["サンプル玲奈", "サンプル美咲"], 2),
    (40, 1, "14:00", "新春サイン会", ["サンプル花子"], 3),
]


class Command(BaseCommand):
    help = "画面確認用のデモデータを投入する（既存のデモデータは置き換える）"

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        Event.objects.filter(sources__source_name=DEMO_SOURCE).delete()
        venues = []
        for name, address, pref, lat, lng in VENUES:
            venue, _ = Venue.objects.update_or_create(
                name=name,
                address=address,
                defaults={"prefecture": pref, "latitude": lat, "longitude": lng},
            )
            venues.append(venue)
        today = timezone.localdate()
        for i, (offset, days, time, title, names, venue_idx) in enumerate(EVENTS, start=1):
            start = today + dt.timedelta(days=offset)
            event = Event.objects.create(
                title=title,
                start_date=start,
                end_date=start + dt.timedelta(days=days - 1),
                start_time=dt.time.fromisoformat(time),
                url="https://example.com/",
                venue=venues[venue_idx],
                raw_venue=venues[venue_idx].name,
                summary=f"{title}のデモ用の概要です。",
                note="デモデータです。実在のイベントではありません。",
            )
            for name in names:
                event.actresses.add(Actress.objects.get_or_create(name=name)[0])
            EventSource.objects.create(
                event=event,
                source_name=DEMO_SOURCE,
                source_url=f"https://example.com/demo/events/{i}",
            )
        self.stdout.write(f"デモデータを {len(EVENTS)} 件投入しました。")
