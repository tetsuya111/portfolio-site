from django.conf import settings
from django.db import models


class AgentConfig(models.Model):
    """エージェントの設定。ロールプロンプトはコードに埋め込まず、ここで差し替える。"""

    HEARING = "hearing"
    SUMMARY = "summary"
    MARKET_ESTIMATE = "market_estimate"
    SELF_ESTIMATE = "self_estimate"

    key = models.SlugField("キー", unique=True)
    name = models.CharField("表示名", max_length=100)
    role_prompt = models.TextField("ロールプロンプト")
    callable_from_chat = models.BooleanField(
        "対話から呼び出せる", default=False,
        help_text="有効にすると、ヒアリングエージェントが依頼者の入力からこのエージェントの呼び出しを提案できる",
    )
    call_description = models.TextField(
        "呼び出しの判断のための説明", blank=True,
        help_text="どんな入力のときに呼び出すべきかを、ヒアリングエージェント向けに書く",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "エージェント"
        verbose_name_plural = "エージェント"

    def __str__(self):
        return f"{self.name} ({self.key})"


class PromptTemplate(models.Model):
    label = models.CharField("表示名", max_length=100)
    prompt = models.TextField("プロンプト")
    sort_order = models.PositiveIntegerField("並び順", default=0)
    is_active = models.BooleanField("有効", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "テンプレ"
        verbose_name_plural = "テンプレ"

    def __str__(self):
        return self.label


class UsageRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField("日付（日本時間）")
    agent_key = models.CharField(max_length=50)
    purpose = models.CharField(max_length=50)
    model = models.CharField(max_length=100, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cache_creation_tokens = models.PositiveIntegerField(default=0)
    cache_read_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "date"])]

    @property
    def total_tokens(self):
        return (
            self.input_tokens + self.output_tokens
            + self.cache_creation_tokens + self.cache_read_tokens
        )
