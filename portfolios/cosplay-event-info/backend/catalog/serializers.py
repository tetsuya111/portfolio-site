"""API のレスポンス形式。収集元の URL は http(s) のものだけを返す（NF-5）。"""

from rest_framework import serializers

from catalog.collector.parsers import is_http_url
from catalog.models import Cosplayer, Event, FetchedPage, Venue


class SafeUrlField(serializers.CharField):
    """http(s) 以外の URL（javascript: など）は空文字で返す。"""

    def to_representation(self, value):
        value = super().to_representation(value)
        return value if is_http_url(value) else ""


class SafeUrlListField(serializers.ListField):
    child = serializers.CharField()

    def to_representation(self, data):
        return [u for u in data or [] if isinstance(u, str) and is_http_url(u)]


class SourceSerializer(serializers.ModelSerializer):
    url = SafeUrlField()

    class Meta:
        model = FetchedPage
        fields = ["url", "fetched_at"]


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["id", "name", "prefecture", "address"]


class EventSerializer(serializers.ModelSerializer):
    url = SafeUrlField()
    source_url = SafeUrlField()
    venue = VenueSerializer(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "url",
            "location_raw",
            "venue",
            "start_date",
            "end_date",
            "notes",
            "source_url",
        ]


class EventDetailSerializer(EventSerializer):
    sources = SourceSerializer(many=True, read_only=True)

    class Meta(EventSerializer.Meta):
        fields = [*EventSerializer.Meta.fields, "sources"]


class VenueEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "name", "start_date", "end_date"]


class VenueWithEventsSerializer(VenueSerializer):
    event_count = serializers.IntegerField()
    events = VenueEventSerializer(source="period_events", many=True)

    class Meta(VenueSerializer.Meta):
        fields = [*VenueSerializer.Meta.fields, "event_count", "events"]


class CosplayerSerializer(serializers.ModelSerializer):
    sns_links = SafeUrlListField()
    source_url = SafeUrlField()

    class Meta:
        model = Cosplayer
        fields = ["id", "name", "sns_links", "career", "description", "notes", "source_url"]


class CosplayerDetailSerializer(CosplayerSerializer):
    sources = SourceSerializer(many=True, read_only=True)

    class Meta(CosplayerSerializer.Meta):
        fields = [*CosplayerSerializer.Meta.fields, "sources"]
