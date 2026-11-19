from django.core.exceptions import ValidationError
from django.db import models

from events.crawler.dedupe import normalize_title


class Actress(models.Model):
    name = models.CharField("名前", max_length=100, unique=True)

    class Meta:
        verbose_name = "女優"
        verbose_name_plural = "女優"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Venue(models.Model):
    name = models.CharField("会場名", max_length=200)
    address = models.CharField("住所", max_length=300, blank=True)
    prefecture = models.CharField("都道府県", max_length=10, blank=True, db_index=True)
    latitude = models.FloatField("緯度", null=True, blank=True)
    longitude = models.FloatField("経度", null=True, blank=True)

    class Meta:
        verbose_name = "会場"
        verbose_name_plural = "会場"
        constraints = [
            models.UniqueConstraint(fields=["name", "address"], name="uniq_venue_name_address")
        ]

    def __str__(self) -> str:
        return self.name


class VenueAlias(models.Model):
    """取り込み時の生の場所文字列と正規化済み会場の対応。"""

    raw_text = models.CharField("元の表記", max_length=300, unique=True)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="aliases")

    class Meta:
        verbose_name = "会場の別表記"
        verbose_name_plural = "会場の別表記"


class Event(models.Model):
    title = models.CharField("イベント名", max_length=300)
    normalized_title = models.CharField(max_length=300, editable=False)
    start_date = models.DateField("開始日", db_index=True)
    end_date = models.DateField("終了日", blank=True)
    start_time = models.TimeField("開始時刻", null=True, blank=True)
    url = models.URLField("リンク", max_length=500, blank=True)
    venue = models.ForeignKey(
        Venue, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    raw_venue = models.CharField("開催場所（元の表記）", max_length=300, blank=True)
    summary = models.TextField("概要", blank=True)
    note = models.TextField("備考", blank=True)
    actresses = models.ManyToManyField(Actress, blank=True, related_name="events")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "イベント"
        verbose_name_plural = "イベント"
        ordering = ["start_date", "start_time", "id"]
        indexes = [models.Index(fields=["venue", "start_date"])]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "終了日は開始日以降にしてください。"})

    def save(self, *args, **kwargs) -> None:
        self.normalized_title = normalize_title(self.title)
        if not self.end_date:
            self.end_date = self.start_date
        super().save(*args, **kwargs)


class EventSource(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="sources")
    source_name = models.CharField("取得元サイト", max_length=50)
    source_url = models.URLField("取得元リンク", max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "取得元"
        verbose_name_plural = "取得元"
        ordering = ["id"]


class FetchedPage(models.Model):
    class Kind(models.TextChoices):
        LIST = "list", "一覧"
        DETAIL = "detail", "詳細"

    class Result(models.TextChoices):
        SUCCESS = "success", "成功"
        FAILED = "failed", "失敗"
        DISALLOWED = "disallowed", "robots.txt で禁止"

    url = models.URLField(max_length=500, unique=True)
    source_name = models.CharField(max_length=50)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    body = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    result = models.CharField(max_length=12, choices=Result.choices, default=Result.SUCCESS)
    error = models.TextField(blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "取得ページ"
        verbose_name_plural = "取得ページ"
