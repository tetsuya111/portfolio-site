"""ログインセッションのメモリ内ストア。トークンはサーバー側にだけ保持する。

セッションには絶対期限・無操作期限・件数上限があり、盗まれた sid の悪用期間とメモリ使用量を抑える。
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

SESSION_MAX_AGE = 7 * 24 * 3600  # 作成からの絶対期限（秒）
SESSION_IDLE_TIMEOUT = 24 * 3600  # 最終利用からの無操作期限（秒）
MAX_SESSIONS = 1000


@dataclass
class Session:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_at: float
    user_id: str
    display_name: str
    # 以下は SessionStore.create() が設定する
    csrf_token: str = field(default="", repr=False)
    created_at: float = 0.0
    last_used_at: float = 0.0


class SessionStore:
    def __init__(
        self, clock: Callable[[], float] = time.time, max_sessions: int = MAX_SESSIONS
    ) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        self._clock = clock
        self._max_sessions = max_sessions

    def _expired(self, session: Session, now: float) -> bool:
        return (
            now - session.created_at > SESSION_MAX_AGE
            or now - session.last_used_at > SESSION_IDLE_TIMEOUT
        )

    def create(self, session: Session) -> str:
        sid = secrets.token_urlsafe(32)
        now = self._clock()
        session.csrf_token = secrets.token_urlsafe(32)
        session.created_at = now
        session.last_used_at = now
        with self._lock:
            for key in [k for k, s in self._sessions.items() if self._expired(s, now)]:
                del self._sessions[key]
            while len(self._sessions) >= self._max_sessions:
                oldest = min(self._sessions, key=lambda k: self._sessions[k].created_at)
                del self._sessions[oldest]
            self._sessions[sid] = session
        return sid

    def get(self, sid: str) -> Session | None:
        if not sid:
            return None
        now = self._clock()
        with self._lock:
            session = self._sessions.get(sid)
            if session is None:
                return None
            if self._expired(session, now):
                del self._sessions[sid]
                return None
            session.last_used_at = now
            return session

    def delete(self, sid: str) -> None:
        with self._lock:
            self._sessions.pop(sid, None)
