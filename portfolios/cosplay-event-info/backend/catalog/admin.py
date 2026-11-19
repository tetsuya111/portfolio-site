from django.contrib import admin

from catalog.models import Cosplayer, Event, FetchedPage, Venue


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "venue")
    list_filter = ("venue__prefecture",)
    search_fields = ("name", "location_raw", "notes")
    date_hierarchy = "start_date"
    filter_horizontal = ("sources",)


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "prefecture", "address")
    search_fields = ("name", "address")


@admin.register(Cosplayer)
class CosplayerAdmin(admin.ModelAdmin):
    list_display = ("name", "source_url")
    search_fields = ("name", "description", "career")
    filter_horizontal = ("sources",)


@admin.register(FetchedPage)
class FetchedPageAdmin(admin.ModelAdmin):
    list_display = ("url", "kind", "status_code", "fetched_at")
    list_filter = ("kind", "status_code")
    search_fields = ("url",)
    readonly_fields = ("fetched_at",)
