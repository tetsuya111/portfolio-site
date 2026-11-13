"""ログインセッションのメモリ内ストア。トークンはサーバー側にだけ保持する。"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field


@dataclass
class Session:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_at: float
    user_id: str
    display_name: str


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, session: Session) -> str:
        sid = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[sid] = session
        return sid

    def get(self, sid: str) -> Session | None:
        if not sid:
            return None
        with self._lock:
            return self._sessions.get(sid)

    def delete(self, sid: str) -> None:
        with self._lock:
            self._sessions.pop(sid, None)
