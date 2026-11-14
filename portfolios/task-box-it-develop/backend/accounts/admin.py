from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AccountUserAdmin(UserAdmin):
    list_display = ("email", "display_name", "role", "is_staff", "date_joined")
    list_filter = ("role", "is_staff")
    search_fields = ("email", "display_name")
    fieldsets = UserAdmin.fieldsets + (
        ("タスク百葉箱", {"fields": ("display_name", "role", "google_sub")}),
    )
