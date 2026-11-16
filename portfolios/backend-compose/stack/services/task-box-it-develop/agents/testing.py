"""テスト用の偽のLLMクライアント。

    @override_settings(LLM_CLIENT_CLASS="agents.testing.FakeLLMClient")

FakeLLMClient.queue に応答を順に積む。応答は次のいずれか:
    "テキスト"                      … 通常の応答
    {"json": {...}}                 … 構造化出力
    {"tool": "call_market_estimate"} … ツールの呼び出し
    LLMError(...)                   … 失敗
"""

import json

from .llm import BaseLLMClient, LLMResult, LLMUsage


class FakeLLMClient(BaseLLMClient):
    queue = []
    calls = []
    usage = LLMUsage(input_tokens=100, output_tokens=50)

    @classmethod
    def reset(cls, *responses):
        cls.queue = list(responses)
        cls.calls = []
        cls.usage = LLMUsage(input_tokens=100, output_tokens=50)

    def stream(self, **kwargs):
        type(self).calls.append(kwargs)
        if not type(self).queue:
            raise AssertionError("FakeLLMClient の応答が足りません")
        response = type(self).queue.pop(0)
        if isinstance(response, Exception):
            raise response
        result = LLMResult(usage=type(self).usage, model="fake-model")
        if isinstance(response, dict) and "tool" in response:
            result.tool_calls = [response["tool"]]
            if response.get("text"):
                yield response["text"]
        elif isinstance(response, dict):
            result.text = json.dumps(response["json"], ensure_ascii=False)
        else:
            result.text = response
            # 差分が複数回に分かれて届くことを模す
            half = len(response) // 2
            for chunk in (response[:half], response[half:]):
                if chunk:
                    yield chunk
        yield result
