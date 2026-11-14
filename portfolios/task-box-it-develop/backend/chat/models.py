from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """対話は1ユーザーにつき1つ。"""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # 同じ対話でLLMを呼ぶ処理が重複して走らないようにするためのフラグ
    processing_started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    class Kind(models.TextChoices):
        CHAT = "chat"
        AGENT_RESULT = "agent_result"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CHAT)
    agent_key = models.CharField(max_length=50, blank=True)
    content = models.TextField()
    # is_estimate / is_preview / completed_items / title など、表示用の付帯情報
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["conversation", "created_at"])]


class PendingAgentCall(models.Model):
    """入力を起点とするエージェント呼び出しの、依頼者の許可待ち。"""

    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        DECLINED = "declined"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="agent_calls"
    )
    agent_key = models.CharField(max_length=50)
    agent_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
