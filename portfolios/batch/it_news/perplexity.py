"""Perplexity API（Chat Completions）の呼び出し。HTTP の送信部分（post）は差し替えられる。"""

from __future__ import annotations

import http.client
import json
import re
import urllib.error
import urllib.request
from typing import Callable

API_URL = "https://api.perplexity.ai/chat/completions"
TIMEOUT_SECONDS = 120

# post(url, headers, body, timeout) -> (HTTP ステータス, 応答本文)
Post = Callable[[str, dict, bytes, int], tuple[int, str]]


class PerplexityError(Exception):
    """API の呼び出し・応答の解析に失敗した。メッセージに API キーを含めない。"""


def urllib_post(url: str, headers: dict, body: bytes, timeout: int) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:  # noqa: S310（URL は API_URL 固定）
            return res.status, res.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def extract_json(content: str) -> object:
    """応答の本文から JSON を取り出す。推論モデルの <think>…</think> とコードフェンスを除く。"""
    text = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    fence = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1)
    return json.loads(text)


def _references(body: dict) -> list[dict]:
    """検索で実際に参照したページ。search_results を優先し、無ければ citations（URL のみ）を使う。"""
    results = body.get("search_results")
    if isinstance(results, list) and results:
        return [
            {"title": str(r.get("title") or r.get("url")), "url": str(r["url"])}
            for r in results
            if isinstance(r, dict) and r.get("url")
        ]
    citations = body.get("citations")
    if isinstance(citations, list):
        return [{"title": str(c), "url": str(c)} for c in citations if isinstance(c, str) and c]
    return []


def call_perplexity(
    *, post: Post, api_key: str, model: str, messages: list[dict], schema: dict, recency: str
) -> tuple[object, list[dict]]:
    """JSON スキーマつきで問い合わせ、(解析した JSON, 参考リンク [{title, url}]) を返す。"""
    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_schema", "json_schema": {"schema": schema}},
        "search_recency_filter": recency,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"}
    try:
        status, text = post(API_URL, headers, json.dumps(payload, ensure_ascii=False).encode("utf-8"), TIMEOUT_SECONDS)
    except (OSError, http.client.HTTPException) as e:
        # 接続できない・応答の途中で切れた（IncompleteRead など）
        raise PerplexityError(f"Perplexity API に接続できませんでした: {type(e).__name__}") from None
    if status != 200:
        # 応答本文にはキーの一部などが含まれうるため、ステータスだけを伝える
        raise PerplexityError(f"Perplexity API がエラーを返しました（HTTP {status}）")
    try:
        body = json.loads(text)
        content = body["choices"][0]["message"]["content"]
        data = extract_json(content)
    except (ValueError, KeyError, IndexError, TypeError):
        raise PerplexityError("Perplexity API の応答を JSON として解析できませんでした") from None
    return data, _references(body)
