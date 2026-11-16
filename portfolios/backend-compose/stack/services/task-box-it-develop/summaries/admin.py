from django.contrib import admin

from .models import RequirementSummary


@admin.register(RequirementSummary)
class RequirementSummaryAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "submitted_at", "handling_status", "mail_status")
    list_filter = ("handling_status", "mail_status")
