"""対話エージェント。

プロンプトのファイルが無い・空のときは、LLMを呼ばずに仮の応答を返す（切り替えの設定は増やさない）。
返信の長さ・記号・金額の抑制は、プロンプトに任せきらずここで担保する。
"""

import logging
import re

from .. import messages as msg
from ..config import get_settings
from .llm import LLMError, get_client

logger = logging.getLogger(__name__)

MAX_LENGTH = 200
# 「お金の話には答えない」の担保。プロンプトの指示だけに頼らない
MONEY_PATTERN = re.compile(r"(\d|[０-９])\s*(円|万|千)|見積|費用|お値段|料金")
# 行頭の記号（箇条書き・見出し・引用）と、強調などの記号だけを落とす。
# 「2回目」のような数字を含む文章を壊さないよう、数字は「1. 」の形のときだけ落とす
LIST_PATTERN = re.compile(r"^[ 	]{0,3}(?:[-*+][ 	]+|\d+[.)][ 	]+|>[ 	]*|#{1,6}[ 	]*)", re.MULTILINE)
INLINE_PATTERN = re.compile(r"[`*_~]")


def load_prompt() -> str:
    path = get_settings().prompt_file
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def to_plain_text(text: str) -> str:
    """Markdownの記号を落とし、200文字程度の短文にする。"""
    plain = INLINE_PATTERN.sub("", LIST_PATTERN.sub("", text))
    plain = re.sub(r"\n{2,}", "\n", plain).strip()
    if len(plain) <= MAX_LENGTH:
        return plain
    # 文の区切りで切る。区切りが見つからなければそのまま切り詰める
    cut = plain[:MAX_LENGTH]
    for mark in ("。", "！", "？", "\n"):
        index = cut.rfind(mark)
        if index >= MAX_LENGTH // 2:
            return cut[: index + 1]
    return cut


def mentions_money(text: str) -> bool:
    return bool(MONEY_PATTERN.search(text))


def build_messages(history: list[tuple[str, str]], text: str) -> list[dict]:
    """ユーザーの入力はシステムプロンプトに連結せず、user ロールで渡す。"""
    conversation = [{"role": role, "content": content} for role, content in history]
    conversation.append({"role": "user", "content": text})
    return conversation


def generate(history: list[tuple[str, str]], text: str) -> str:
    """対話の返信を作る。LLMの失敗は LLMError のまま呼び出し元へ返す。"""
    prompt = load_prompt()
    if not prompt:
        # プロンプトが未作成のうちは仮の応答（LLMを呼ばない）
        return msg.DIALOGUE_PLACEHOLDER
    answer = get_client().complete(prompt, build_messages(history, text))
    if not answer.strip():
        raise LLMError("空の応答")
    if mentions_money(answer) or mentions_money(text):
        url = get_settings().contract_page_url
        return msg.ESTIMATE_GUIDE + (f"\n{url}" if url else "")
    return to_plain_text(answer)
