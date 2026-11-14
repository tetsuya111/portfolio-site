"""エージェント = ロールプロンプトを持ち、入力を与えると出力を返すだけの薄いクラス。

エージェントは他のエージェントを参照しない。エージェントをまたぐ処理は、
呼び出し側（chat.services）が順に run() を呼んで仲介する。
"""

from .llm import LLMError, LLMResult, get_llm_client
from .models import AgentConfig
from .usage import record_usage


class Agent:
    def __init__(self, config, user, client=None):
        self.config = config
        self.user = user
        self.client = client or get_llm_client()

    @classmethod
    def load(cls, key, user, client=None):
        return cls(AgentConfig.objects.get(key=key), user, client)

    def _messages(self, input_text, history):
        messages = list(history or [])
        if input_text is not None:
            messages.append({"role": "user", "content": input_text})
        return messages

    def stream(self, input_text=None, *, history=None, purpose, tools=None, tool_choice=None):
        """テキストの差分を順に yield し、最後に LLMResult を yield する。"""
        try:
            for item in self.client.stream(
                system=self.config.role_prompt,
                messages=self._messages(input_text, history),
                tools=tools,
                tool_choice=tool_choice,
            ):
                if isinstance(item, LLMResult):
                    record_usage(self.user, self.config.key, purpose, item)
                yield item
        except LLMError as exc:
            self._record_failed(exc, purpose)
            raise

    def run(self, input_text=None, *, history=None, purpose, output_schema=None,
            tools=None, tool_choice=None):
        try:
            result = self.client.complete(
                system=self.config.role_prompt,
                messages=self._messages(input_text, history),
                tools=tools,
                tool_choice=tool_choice,
                output_schema=output_schema,
            )
        except LLMError as exc:
            self._record_failed(exc, purpose)
            raise
        record_usage(self.user, self.config.key, purpose, result)
        return result

    def _record_failed(self, exc, purpose):
        # 拒否・打ち切りでもトークンは消費されているため、使用量に含める
        result = getattr(exc, "result", None)
        if result is not None:
            record_usage(self.user, self.config.key, purpose, result)
