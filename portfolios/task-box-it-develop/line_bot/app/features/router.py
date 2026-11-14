"""イベントの振り分け。

機能の判定は postback の `data`（固定値）で行い、メッセージの先頭の文字列では判定しない。
例外はユーザー情報の登録のフォーマットだけで、LIFFが使えない場合の入り口を塞がないため。
"""

import logging

from .. import messages as msg
from ..config import get_settings
from ..db import session_scope
from ..line.client import Blocked, LineApiError, get_client
from ..models import User
from . import dialogue, registration

logger = logging.getLogger(__name__)

TEXT = "text"
POSTBACK = "postback"
ACTIONS = ("register", "meeting", "contract")


def extract_events(payload: dict) -> list[dict]:
    """Webhookのボディから、扱うイベントだけを取り出して正規化する。"""
    events = []
    for event in payload.get("events") or []:
        event_id = event.get("webhookEventId")
        user_id = (event.get("source") or {}).get("userId")
        if not event_id or not user_id:
            continue
        reply_token = event.get("replyToken")
        if event.get("type") == "message" and (event.get("message") or {}).get("type") == "text":
            events.append({
                "type": TEXT, "event_id": event_id, "user_id": user_id,
                "reply_token": reply_token, "text": (event["message"].get("text") or "").strip(),
            })
        elif event.get("type") == POSTBACK:
            events.append({
                "type": POSTBACK, "event_id": event_id, "user_id": user_id,
                "reply_token": reply_token, "data": (event.get("postback") or {}).get("data", ""),
            })
        # それ以外（スタンプ・画像・follow / unfollow・グループ招待など）は無視する
    return events


def parse_action(data: str) -> str | None:
    for key, _, value in [data.partition("=")]:
        if key == "action" and value in ACTIONS:
            return value
    return None


class Responder:
    """返信を1通に保つ。reply token が使えるうちは reply（通数を消費しない）。"""

    def __init__(self, client, reply_token: str | None):
        self.client = client
        self.reply_token = reply_token
        self.sent = False

    def send(self, line_user_id: str, text: str) -> None:
        if self.sent:
            return
        self.sent = True
        try:
            if self.reply_token:
                self.client.reply(self.reply_token, text)
            else:
                self.client.push(line_user_id, text)
        except Blocked:
            logger.info("ブロック済みのため送信しません: user=%s", line_user_id)
        except LineApiError as exc:
            logger.warning("送信に失敗: user=%s reason=%s", line_user_id, exc)


def is_dialogue(event: dict) -> bool:
    """待機メッセージを先に返すべきイベントか（契約者の、登録ではないテキスト）。"""
    if event["type"] != TEXT or registration.matches(event["text"]) or not event["text"]:
        return False
    with session_scope() as session:
        user = session.get(User, event["user_id"])
        return user is not None and user.is_contracted


def handle_event(event: dict) -> None:
    """ジョブの本体。1イベントを処理して1通返す。"""
    client = get_client()
    settings = get_settings()
    responder = Responder(client, event.get("reply_token"))
    with session_scope() as session:
        user = session.get(User, event["user_id"])
        if event["type"] == POSTBACK:
            action = parse_action(event.get("data", ""))
            if action == "register":
                liff_url = f"https://liff.line.me/{settings.liff_id}" if settings.liff_id else ""
                responder.send(event["user_id"], msg.register_guide(liff_url))
            elif action == "meeting":
                responder.send(event["user_id"], msg.UNDER_CONSTRUCTION)
            elif action == "contract":
                url = settings.contract_page_url
                responder.send(
                    event["user_id"],
                    msg.contract_guide(url) if url else msg.UNDER_CONSTRUCTION,
                )
            return

        text = event["text"]
        if registration.matches(text):
            responder.send(
                event["user_id"], registration.register_from_text(session, event["user_id"], text)
            )
            return
        if user is None:
            responder.send(event["user_id"], f"{msg.NOT_CONTRACTED}\n{msg.NEED_REGISTRATION}")
            return
        if not user.is_contracted:
            responder.send(event["user_id"], msg.NOT_CONTRACTED)
            return
    # 契約者の対話。待機メッセージは受信時に返しているため、ここではLLMの回答だけを送る
    dialogue.run(event["user_id"], event["text"])
