"""契約者との対話（会話履歴の保存を含む）。

workerで実行される。回答は Push メッセージで送る（reply token は待機メッセージで使い切るため）。
"""

import logging

from sqlalchemy import delete, select

from .. import messages as msg
from ..agents import dialogue as agent
from ..agents.llm import LLMError
from ..config import get_settings
from ..db import session_scope
from ..line.client import Blocked, LineApiError, get_client
from ..models import ConversationTurn, User
from ..usage import consume

logger = logging.getLogger(__name__)


def load_history(session, line_user_id: str) -> list[tuple[str, str]]:
    """そのユーザー自身の直近のやり取りだけを、古い順に返す。"""
    limit = get_settings().history_max_turns * 2
    rows = session.scalars(
        select(ConversationTurn)
        .where(ConversationTurn.line_user_id == line_user_id)
        .order_by(ConversationTurn.created_at.desc(), ConversationTurn.id.desc())
        .limit(limit)
    ).all()
    return [(row.role, row.content) for row in reversed(rows)]


def save_turn(session, line_user_id: str, question: str, answer: str) -> None:
    session.add(ConversationTurn(line_user_id=line_user_id, role="user", content=question))
    session.add(ConversationTurn(line_user_id=line_user_id, role="assistant", content=answer))
    session.flush()
    trim_history(session, line_user_id)


def trim_history(session, line_user_id: str) -> None:
    """直近の往復数を超えた分を、古いものから消す。"""
    keep = get_settings().history_max_turns * 2
    ids = session.scalars(
        select(ConversationTurn.id)
        .where(ConversationTurn.line_user_id == line_user_id)
        .order_by(ConversationTurn.created_at.desc(), ConversationTurn.id.desc())
        .offset(keep)
    ).all()
    if ids:
        session.execute(delete(ConversationTurn).where(ConversationTurn.id.in_(ids)))


def run(line_user_id: str, text: str) -> None:
    """ジョブの本体。LLMを呼び、回答をPushで送る。"""
    client = get_client()
    with session_scope() as session:
        user = session.get(User, line_user_id)
        if user is None or not user.is_contracted:
            # 実行までの間に契約状態が変わった場合
            _send(client, line_user_id, msg.NOT_CONTRACTED)
            return
        if not consume(session, user):
            _send(client, line_user_id, msg.LIMIT_REACHED)
            return
        history = load_history(session, line_user_id)
        try:
            answer = agent.generate(history, text)
        except LLMError as exc:
            # 失敗の種類だけを残す。本文は残さない
            logger.warning("LLMの呼び出しに失敗: user=%s reason=%s", line_user_id, exc)
            _send(client, line_user_id, msg.LLM_FAILED)
            return
        save_turn(session, line_user_id, text, answer)
    _send(client, line_user_id, answer)


def _send(client, line_user_id: str, text: str) -> None:
    try:
        client.push(line_user_id, text)
    except Blocked:
        logger.info("ブロック済みのため送信しません: user=%s", line_user_id)
    except LineApiError as exc:
        logger.warning("送信に失敗: user=%s reason=%s", line_user_id, exc)
