"""読み取り専用の API（イベント・会場・コスプレイヤー）。"""

from datetime import date, timedelta

from django.db.models import Count, Prefetch, Q, QuerySet
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from catalog.models import Cosplayer, Event, Venue
from catalog.serializers import (
    CosplayerDetailSerializer,
    CosplayerSerializer,
    EventDetailSerializer,
    EventSerializer,
    VenueWithEventsSerializer,
)

DEFAULT_MAP_PERIOD_DAYS = 30
MAX_VENUES = 200


class StandardPagination(PageNumberPagination):
    page_size = 20


def _date_param(request: Request, name: str) -> date | None:
    value = request.query_params.get(name, "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({name: "日付は YYYY-MM-DD 形式で指定してください。"}) from exc


def _period(request: Request) -> tuple[date | None, date | None]:
    start, end = _date_param(request, "from"), _date_param(request, "to")
    if start and end and start > end:
        raise ValidationError({"to": "終了日は開始日以降を指定してください。"})
    return start, end


def _overlapping(start: date | None, end: date | None, prefix: str = "") -> Q:
    """開催期間が [start, end] と重なる条件（EV-9）。"""
    condition = Q()
    if start:
        condition &= Q(**{f"{prefix}end_date__gte": start})
    if end:
        condition &= Q(**{f"{prefix}start_date__lte": end})
    return condition


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination

    def get_serializer_class(self):
        return EventDetailSerializer if self.action == "retrieve" else EventSerializer

    def get_queryset(self) -> QuerySet[Event]:
        queryset = Event.objects.select_related("venue").order_by("start_date", "id")
        if self.action == "retrieve":
            return queryset.prefetch_related("sources")

        params = self.request.query_params
        keyword = params.get("q", "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(location_raw__icontains=keyword)
                | Q(venue__name__icontains=keyword)
                | Q(notes__icontains=keyword)
            )
        queryset = queryset.filter(_overlapping(*_period(self.request)))
        prefecture = params.get("prefecture", "").strip()
        if prefecture:
            queryset = queryset.filter(venue__prefecture=prefecture)
        return queryset


@api_view(["GET"])
def venues_in_period(request: Request) -> Response:
    """期間内にイベントがある会場と件数（MAP-1）。期間の既定は今日から30日間。"""
    start, end = _period(request)
    start = start or timezone.localdate()
    end = end or start + timedelta(days=DEFAULT_MAP_PERIOD_DAYS)
    if start > end:
        raise ValidationError({"to": "終了日は開始日以降を指定してください。"})

    in_period = _overlapping(start, end, prefix="events__")
    venues = (
        Venue.objects.annotate(event_count=Count("events", filter=in_period))
        .filter(event_count__gt=0)
        .order_by("-event_count", "name")
        .prefetch_related(
            Prefetch(
                "events",
                queryset=Event.objects.filter(_overlapping(start, end)).order_by(
                    "start_date", "id"
                ),
                to_attr="period_events",
            )
        )[:MAX_VENUES]
    )
    return Response(VenueWithEventsSerializer(venues, many=True).data)


class CosplayerViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination

    def get_serializer_class(self):
        return CosplayerDetailSerializer if self.action == "retrieve" else CosplayerSerializer

    def get_queryset(self) -> QuerySet[Cosplayer]:
        queryset = Cosplayer.objects.order_by("name", "id")
        if self.action == "retrieve":
            return queryset.prefetch_related("sources")
        keyword = self.request.query_params.get("q", "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(career__icontains=keyword)
            )
        return queryset
