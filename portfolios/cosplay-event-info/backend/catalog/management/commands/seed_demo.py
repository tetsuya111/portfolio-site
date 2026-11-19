"""デモ用のイベント・会場・コスプレイヤーを投入する（通信なし・何度実行しても同じ件数）。

イベント名・人物はすべて架空。開催日は実行日からの相対日付で、常に「これから」のイベントになる。
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.collector.importer import resolve_venue
from catalog.collector.normalizer import RuleBasedNormalizer
from catalog.models import Cosplayer, Event

DEMO_NOTE = "デモ用の架空のデータです。"

# (イベント名, 開催場所, 開始日までの日数, 開催日数, 備考)
DEMO_EVENTS = [
    (
        "デモ・ウィンターコスプレフェス",
        "東京ビッグサイト 西3・4ホール",
        3,
        2,
        "大型の屋内イベント。更衣室あり。",
    ),
    ("デモ・湾岸コスプレ撮影会", "幕張メッセ 国際展示場9ホール", 7, 1, "屋外撮影エリアあり。"),
    ("デモ・なにわコスプレカーニバル", "インテックス大阪 5号館", 10, 2, "物販ブースあり。"),
    ("デモ・港まちコスプレ祭", "ポートメッセなごや 第1展示館", 14, 1, ""),
    (
        "デモ・池袋ストリートコス",
        "池袋サンシャインシティ 文化会館",
        17,
        2,
        "街中での撮影は指定エリアのみ。",
    ),
    ("デモ・ドームシティコスプレの日", "東京ドームシティ プリズムホール", 21, 1, ""),
    ("デモ・九州コスプレサミット", "西日本総合展示場 新館", 28, 2, "九州最大級。"),
    ("デモ・杜の都コスプレフェスタ", "夢メッセみやぎ", 35, 1, ""),
    ("デモ・新春コスプレ撮影会", "東京ビッグサイト 南1ホール", 45, 1, "新年最初の撮影会。"),
    ("デモ・春のコスプレ交流会", "大阪府大阪市 中央区民ホール", 60, 1, "初心者向けの交流会。"),
    ("デモ・夜景コスプレ撮影会", "幕張メッセ イベントホール", 75, 1, "夜間の撮影がメイン。"),
    (
        "デモ・コスプレ衣装づくり講座",
        "福岡県福岡市 博多市民センター",
        90,
        1,
        "衣装制作のワークショップ。",
    ),
]

# (名前, 説明文, 経歴, SNS)
DEMO_COSPLAYERS = [
    ("デモ 花子", "アニメ・ゲームのキャラクターを中心に活動するコスプレイヤー。",
     "2016年に活動を開始。2021年に写真集を発売。", ["https://example.com/demo/hanako/x"]),
    ("デモ 太郎", "甲冑や武器などの造形を得意とするコスプレイヤー。",
     "2014年から造形を始め、国内外の大会に出場。", ["https://example.com/demo/taro/x",
                                                "https://example.com/demo/taro/instagram"]),
    ("デモ ゆき", "和装のキャラクターを多く手がける。",
     "2019年に活動を開始。地方イベントの公式コスプレイヤーを務める。", []),
    ("デモ れん", "撮影会の主催も行うコスプレイヤー兼カメラマン。",
     "2012年から活動。2020年より撮影会を主催。", ["https://example.com/demo/ren/youtube"]),
    ("デモ みお", "SF 作品のキャラクターの再現度に定評がある。",
     "2018年に活動を開始。衣装制作の講座も担当。", ["https://example.com/demo/mio/x"]),
    ("デモ そら", "ダンス動画と組み合わせた発信を行う。",
     "2022年に活動を開始。動画投稿サイトを中心に活動。", ["https://example.com/demo/sora/tiktok"]),
]  # fmt: skip


class Command(BaseCommand):
    help = "デモ用のイベント・会場・コスプレイヤーを投入する"

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()
        normalizer = RuleBasedNormalizer()
        for name, location, offset, days, notes in DEMO_EVENTS:
            start = today + timedelta(days=offset)
            Event.objects.update_or_create(
                name=name,
                defaults={
                    "location_raw": location,
                    "venue": resolve_venue(location, normalizer),
                    "start_date": start,
                    "end_date": start + timedelta(days=days - 1),
                    "notes": f"{notes}{DEMO_NOTE}",
                },
            )
        for name, description, career, sns in DEMO_COSPLAYERS:
            Cosplayer.objects.update_or_create(
                name=name,
                defaults={
                    "description": description,
                    "career": career,
                    "sns_links": sns,
                    "notes": DEMO_NOTE,
                },
            )
        self.stdout.write(
            f"デモデータを投入しました（イベント {len(DEMO_EVENTS)} 件、"
            f"コスプレイヤー {len(DEMO_COSPLAYERS)} 人）"
        )
