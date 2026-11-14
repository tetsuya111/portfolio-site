"""APIキーなしで画面の動きを確認するための、開発専用のLLMクライアント。

    LLM_CLIENT_CLASS=agents.demo.DemoLLMClient

実際のLLMは呼ばず、決まった応答を返す。プロンプトの品質の確認には使えない。
"""

import json
import time

from .llm import BaseLLMClient, LLMResult, LLMUsage

DEMO_SUMMARY = """# 目的
（デモ）予約の受付を楽にする

# ほしい機能
- 予約の登録と一覧

# 期間のレンジ
1か月以内（仮）

# 予算のレンジ
5〜10万円（仮）

# ゴール(最低基準)
予約を一覧で見られること

# セキュリティ
ログインした人だけが見られること（仮）
"""

DEMO_MOCK = """こんな画面のイメージです。

```html
<div style="font-family:sans-serif;padding:16px">
  <h1 style="font-size:20px">予約の一覧（デモ）</h1>
  <table border="1" cellpadding="6" style="border-collapse:collapse">
    <tr><th>日時</th><th>お名前</th></tr>
    <tr><td>10/1 10:00</td><td>山田さま</td></tr>
  </table>
  <button style="margin-top:12px">予約を追加</button>
  <script>document.body.innerHTML = "スクリプトが動いています（動いてはいけません）"</script>
</div>
```
"""


def _last_user_text(messages):
    for message in reversed(messages):
        if message["role"] == "user":
            return message["content"]
    return ""


class DemoLLMClient(BaseLLMClient):
    def stream(self, *, system, messages, tools=None, tool_choice=None, output_schema=None):
        text = _last_user_text(messages)
        result = LLMResult(usage=LLMUsage(input_tokens=len(str(messages)), output_tokens=200), model="demo")
        if output_schema is not None:
            earlier = " ".join(m["content"] for m in messages[:-1] if m["role"] == "user")
            result.text = json.dumps(
                self._structured(output_schema, text, earlier), ensure_ascii=False
            )
            yield result
            return

        if tools and tool_choice is None:
            for keyword, tool in (("相場", "call_market_estimate"), ("見積", "call_self_estimate"),
                                  ("要件サマリー作成", "call_summary")):
                if keyword in text:
                    result.tool_calls = [tool]
                    yield result
                    return

        if "画面のイメージ" in text:
            reply = DEMO_MOCK
        elif not tools:
            reply = "（デモの見積もり）\n\n| 項目 | 金額 |\n| --- | --- |\n| 開発 | 50,000円 |\n| 修正 | 10,000円 |\n\n合計: **60,000円**"
        else:
            reply = f"（デモの応答）なるほど、「{text[:40]}」ですね。もう少し詳しく教えてもらえますか？"
        for index in range(0, len(reply), 8):
            time.sleep(0.03)
            yield reply[index:index + 8]
        result.text = reply
        yield result

    def _structured(self, schema, text, earlier):
        properties = schema["properties"]
        if "complete" in properties:
            # 依頼者が「予算」に一度も触れていなければ、不足ありとして返す
            return {"complete": True, "missing": []} if "予算" in earlier else {
                "complete": False, "missing": ["予算のレンジ"]}
        if "requirements_markdown" in properties:
            preview = "（仮）" in text
            return {"requirements_markdown": DEMO_SUMMARY,
                    "completed_items": ["期間のレンジ", "予算のレンジ", "セキュリティ"] if preview else []}
        return {"status": "ok", "title": "予約管理ツール（デモ）", "body_markdown": DEMO_SUMMARY,
                "missing_terms": [], "message": ""}
