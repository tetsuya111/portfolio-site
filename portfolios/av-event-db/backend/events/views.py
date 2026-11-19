"""読み取り専用 API（REQ-5, REQ-6, NFR-2）。"""

import datetime as dt

from django.db.models import Prefetch, Q, QuerySet
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Actress, Event, EventSource
from .serializers import (
    EventDetailSerializer,
    EventListSerializer,
    MapEventSerializer,
    VenueDetailSerializer,
)

MAP_DEFAULT_DAYS = 30
MAP_MAX_DAYS = 366


@api_view(["GET"])
def health(request: Request) -> Response:
    return Response({"status": "ok"})


def _parse_date(params, name: str) -> dt.date | None:
    value = params.get(name)
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({name: "日付は YYYY-MM-DD で指定してください。"}) from exc


def _period(params) -> tuple[dt.date | None, dt.date | None]:
    start, end = _parse_date(params, "from"), _parse_date(params, "to")
    if start and end and start > end:
        raise ValidationError({"to": "終了日は開始日以降にしてください。"})
    return start, end


def _overlapping(qs: QuerySet[Event], start: dt.date | None, end: dt.date | None):
    """開催期間が [start, end] と重なるイベントに絞る。"""
    if start:
        qs = qs.filter(end_date__gte=start)
    if end:
        qs = qs.filter(start_date__lte=end)
    return qs


class EventPagination(PageNumberPagination):
    page_size = 20

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data["total_pages"] = self.page.paginator.num_pages
        return response


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = EventPagination

    def get_serializer_class(self):
        return EventDetailSerializer if self.action == "retrieve" else EventListSerializer

    def get_queryset(self) -> QuerySet[Event]:
        qs = (
            Event.objects.select_related("venue")
            .prefetch_related(Prefetch("actresses", queryset=Actress.objects.order_by("name")))
            .order_by("start_date", "start_time", "id")
        )
        if self.action == "retrieve":
            return qs.prefetch_related(
                Prefetch("sources", queryset=EventSource.objects.order_by("id"))
            )
        params = self.request.query_params
        qs = _overlapping(qs, *_period(params))
        if prefecture := params.get("prefecture"):
            qs = qs.filter(venue__prefecture=prefecture)
        if q := params.get("q", "").strip():
            matched = Event.objects.filter(
                Q(title__icontains=q)
                | Q(summary__icontains=q)
                | Q(note__icontains=q)
                | Q(actresses__name__icontains=q)
                | Q(venue__name__icontains=q)
            ).values("id")
            qs = qs.filter(id__in=matched)
        return qs


@api_view(["GET"])
def map_venues(request: Request) -> Response:
    """期間内にイベントがある会場と、その会場の期間内イベント（REQ-6）。"""
    start, end = _period(request.query_params)
    today = timezone.localdate()
    start = start or (end - dt.timedelta(days=MAP_DEFAULT_DAYS) if end else today)
    end = end or start + dt.timedelta(days=MAP_DEFAULT_DAYS)
    if (end - start).days > MAP_MAX_DAYS:
        raise ValidationError({"to": f"期間は {MAP_MAX_DAYS} 日以内で指定してください。"})
    events = (
        _overlapping(Event.objects.filter(venue__isnull=False), start, end)
        .select_related("venue")
        .order_by("start_date", "start_time", "id")
    )
    grouped: dict[int, dict] = {}
    for event in events:
        assert event.venue is not None  # noqa: S101 - venue__isnull=False で絞り込み済み
        entry = grouped.get(event.venue_id)
        if entry is None:
            entry = grouped[event.venue_id] = {
                **VenueDetailSerializer(event.venue).data,
                "events": [],
            }
        entry["events"].append(MapEventSerializer(event).data)
    return Response(list(grouped.values()))
