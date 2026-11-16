"""LLM呼び出しのラッパー。

呼び出しはすべてここを通す。テストでは settings.LLM_CLIENT_CLASS を偽のクライアントに
差し替え、実際のAPIは呼ばない。
"""

import json
import logging
import time
from dataclasses import dataclass, field

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM呼び出しの失敗。retryable は時間をおけば成功しうるかどうか。"""

    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


class LLMRefusal(LLMError):
    pass


class LLMTruncated(LLMError):
    pass


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0


@dataclass
class LLMResult:
    text: str = ""
    # モデルが呼び出しを求めたツール名（実行はしない）
    tool_calls: list = field(default_factory=list)
    usage: LLMUsage = field(default_factory=LLMUsage)
    model: str = ""

    def parsed(self):
        """構造化出力（output_schema つきの呼び出し）の結果を dict で返す。"""
        try:
            return json.loads(self.text)
        except json.JSONDecodeError as exc:
            raise LLMError("構造化出力を解釈できませんでした") from exc


class BaseLLMClient:
    def stream(self, *, system, messages, tools=None, tool_choice=None, output_schema=None):
        """テキストの差分（str）を順に yield し、最後に LLMResult を yield する。"""
        raise NotImplementedError

    def complete(self, **kwargs):
        result = None
        for item in self.stream(**kwargs):
            if isinstance(item, LLMResult):
                result = item
        if result is None:
            raise LLMError("LLMから応答が得られませんでした")
        return result


class AnthropicLLMClient(BaseLLMClient):
    def __init__(self):
        import anthropic

        self._anthropic = anthropic
        # 認証情報は環境変数（ANTHROPIC_API_KEY など）からSDKが解決する
        self._client = anthropic.Anthropic()

    def _request_kwargs(self, system, messages, tools, tool_choice, output_schema):
        output_config = {"effort": settings.LLM_EFFORT}
        if output_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": output_schema}
        kwargs = {
            "model": settings.LLM_MODEL,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "system": system,
            "messages": messages,
            "thinking": {"type": "adaptive"},
            "output_config": output_config,
            # 対話履歴は毎回すべて送るため、直前までの接頭辞をキャッシュさせる
            "cache_control": {"type": "ephemeral"},
        }
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
        return kwargs

    def stream(self, *, system, messages, tools=None, tool_choice=None, output_schema=None):
        anthropic = self._anthropic
        kwargs = self._request_kwargs(system, messages, tools, tool_choice, output_schema)
        started = time.monotonic()
        try:
            # 長い出力でHTTPタイムアウトにならないよう、完了を待つだけの場合もストリーミングで呼ぶ
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text
                message = stream.get_final_message()
        except anthropic.RateLimitError as exc:
            raise LLMError("レート制限に達しました", retryable=True) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("LLMに接続できませんでした", retryable=True) from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(
                f"LLMのAPIエラー ({exc.status_code})", retryable=exc.status_code >= 500
            ) from exc

        usage = LLMUsage(
            input_tokens=message.usage.input_tokens or 0,
            output_tokens=message.usage.output_tokens or 0,
            cache_creation_tokens=message.usage.cache_creation_input_tokens or 0,
            cache_read_tokens=message.usage.cache_read_input_tokens or 0,
        )
        logger.info(
            "llm call model=%s stop_reason=%s seconds=%.1f in=%d out=%d cache_w=%d cache_r=%d",
            message.model, message.stop_reason, time.monotonic() - started,
            usage.input_tokens, usage.output_tokens,
            usage.cache_creation_tokens, usage.cache_read_tokens,
        )
        result = LLMResult(
            text="".join(b.text for b in message.content if b.type == "text"),
            tool_calls=[b.name for b in message.content if b.type == "tool_use"],
            usage=usage,
            model=message.model,
        )
        # 使用量は失敗時も記録できるよう、例外に結果を持たせる
        if message.stop_reason == "refusal":
            error = LLMRefusal("LLMが応答を拒否しました")
            error.result = result
            raise error
        if message.stop_reason == "max_tokens":
            error = LLMTruncated("LLMの出力が途中で打ち切られました")
            error.result = result
            raise error
        yield result


def get_llm_client():
    return import_string(settings.LLM_CLIENT_CLASS)()
