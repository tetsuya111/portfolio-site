from rest_framework import serializers

from .models import Event, EventSource, Venue


class VenueSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["id", "name", "prefecture"]


class VenueDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["id", "name", "address", "prefecture", "latitude", "longitude"]


class EventSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSource
        fields = ["source_name", "source_url"]


class EventListSerializer(serializers.ModelSerializer):
    venue = VenueSummarySerializer(allow_null=True)
    actresses = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    class Meta:
        model = Event
        fields = ["id", "title", "start_date", "end_date", "start_time", "venue", "actresses"]


class EventDetailSerializer(EventListSerializer):
    venue = VenueDetailSerializer(allow_null=True)
    sources = EventSourceSerializer(many=True, read_only=True)

    class Meta(EventListSerializer.Meta):
        fields = [
            *EventListSerializer.Meta.fields,
            "url",
            "raw_venue",
            "summary",
            "note",
            "sources",
        ]


class MapEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "title", "start_date", "end_date", "start_time"]
