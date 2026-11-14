"""LLMのクライアント。テストでは FakeLLMClient に差し替え、実際のAPIを呼ばない。"""

import importlib
import logging

from ..config import get_settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class BaseLLMClient:
    def complete(self, system: str, messages: list[dict]) -> str:
        raise NotImplementedError


class AnthropicLLMClient(BaseLLMClient):
    def complete(self, system: str, messages: list[dict]) -> str:
        import anthropic

        settings = get_settings()
        if not settings.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY が設定されていません")
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        try:
            response = client.messages.create(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                system=system,
                messages=messages,
            )
        except Exception as exc:  # タイムアウト・APIエラー・レート制限
            raise LLMError(f"{type(exc).__name__}") from exc
        return "".join(block.text for block in response.content if block.type == "text")


class FakeLLMClient(BaseLLMClient):
    """テスト用。queue に積んだ応答を順に返す。例外を積むと失敗を再現できる。"""

    queue: list = []
    calls: list[tuple[str, list[dict]]] = []

    @classmethod
    def reset(cls, *responses):
        cls.queue = list(responses)
        cls.calls = []

    def complete(self, system: str, messages: list[dict]) -> str:
        type(self).calls.append((system, messages))
        if not type(self).queue:
            raise AssertionError("FakeLLMClient の応答が足りません")
        response = type(self).queue.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def get_client() -> BaseLLMClient:
    path = get_settings().llm_client_class
    module_name, _, class_name = path.rpartition(".")
    return getattr(importlib.import_module(module_name), class_name)()
