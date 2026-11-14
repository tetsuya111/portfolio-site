from django.contrib import admin

from .models import AgentConfig, PromptTemplate, UsageRecord


@admin.register(AgentConfig)
class AgentConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "callable_from_chat", "updated_at")


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ("label", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "agent_key", "purpose", "input_tokens",
                    "output_tokens", "cache_creation_tokens", "cache_read_tokens")
    list_filter = ("date", "agent_key")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
