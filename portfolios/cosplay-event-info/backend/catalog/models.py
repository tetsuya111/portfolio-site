"""イベント・コスプレイヤーと、収集したページのログのモデル。"""

from django.db import models


class FetchedPage(models.Model):
    """バッチが取得したページのログ（FT-1）。成功したページは再取得しない（FT-2）。"""

    class Kind(models.TextChoices):
        EVENT = "event", "イベント"
        COSPLAYER = "cosplayer", "コスプレイヤー"

    url = models.URLField("URL", max_length=2000, unique=True)
    final_url = models.URLField("リダイレクト後の URL", max_length=2000, blank=True)
    kind = models.CharField("種別", max_length=20, choices=Kind.choices)
    status_code = models.PositiveSmallIntegerField("HTTP ステータス", null=True, blank=True)
    content = models.TextField("本文", blank=True)
    error = models.TextField("エラー", blank=True)
    fetched_at = models.DateTimeField("取得日時", auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = "取得したページ"
        ordering = ["-fetched_at"]

    def __str__(self) -> str:
        return self.url

    @property
    def is_success(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 300


class Venue(models.Model):
    """正規化した会場（EV-4）。地図表示の単位になる。"""

    name = models.CharField("会場名", max_length=200, unique=True)
    prefecture = models.CharField("都道府県", max_length=10, blank=True, db_index=True)
    address = models.CharField("住所", max_length=300, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "会場"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Event(models.Model):
    name = models.CharField("イベント名", max_length=300)
    url = models.URLField("リンク", max_length=2000, blank=True)
    location_raw = models.CharField("開催場所（取得元の表記）", max_length=300, blank=True)
    venue = models.ForeignKey(
        Venue,
        verbose_name="会場",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    start_date = models.DateField("開始日", db_index=True)
    end_date = models.DateField("終了日")
    notes = models.TextField("備考", blank=True)
    source_url = models.URLField("取得元リンク", max_length=2000, blank=True)
    sources = models.ManyToManyField(
        FetchedPage, verbose_name="取得元", blank=True, related_name="events"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = "イベント"
        ordering = ["start_date", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="event_end_date_gte_start_date",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name}（{self.start_date}）"


class Cosplayer(models.Model):
    name = models.CharField("名前", max_length=200, db_index=True)
    sns_links = models.JSONField("SNS のリンク", default=list, blank=True)
    career = models.TextField("経歴", blank=True)
    description = models.TextField("説明文", blank=True)
    notes = models.TextField("備考", blank=True)
    source_url = models.URLField("取得元リンク", max_length=2000, blank=True)
    sources = models.ManyToManyField(
        FetchedPage, verbose_name="取得元", blank=True, related_name="cosplayers"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = "コスプレイヤー"
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name
