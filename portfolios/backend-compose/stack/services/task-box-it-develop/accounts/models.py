from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        GENERAL = "general", "一般ユーザー"
        ADMIN = "admin", "管理者"

    email = models.EmailField("メールアドレス", unique=True)
    # メールアドレスは変わりうるため、ユーザーの同定にはGoogleのユーザーIDを使う
    google_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)
    display_name = models.CharField("ユーザー名", max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GENERAL)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    def __str__(self):
        return self.display_name or self.email
