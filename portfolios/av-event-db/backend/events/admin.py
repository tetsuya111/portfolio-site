from django.contrib import admin

from . import models

admin.site.register(
    [models.Actress, models.Venue, models.VenueAlias, models.EventSource, models.FetchedPage]
)


@admin.register(models.Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "start_date", "end_date", "venue"]
    search_fields = ["title", "actresses__name"]
