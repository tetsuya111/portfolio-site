from django.conf import settings
from django.db import models


class RequirementSummary(models.Model):
    class HandlingStatus(models.TextChoices):
        NEW = "new", "未対応"
        IN_PROGRESS = "in_progress", "対応中"
        DONE = "done", "対応済み"

    class MailStatus(models.TextChoices):
        PENDING = "pending", "未送信"
        SENT = "sent", "送信済み"
        FAILED = "failed", "送信失敗"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    title = models.CharField(max_length=100)
    body_markdown = models.TextField()
    # null の間は下書き（依頼者が「確定」を押す前の表示用）。管理者画面には送信済みのみ出す
    submitted_at = models.DateTimeField(null=True, blank=True)
    handling_status = models.CharField(
        max_length=20, choices=HandlingStatus.choices, default=HandlingStatus.NEW
    )
    mail_status = models.CharField(
        max_length=20, choices=MailStatus.choices, default=MailStatus.PENDING
    )
    mail_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["submitted_at"]),
            models.Index(fields=["handling_status"]),
        ]

    def __str__(self):
        return self.title
