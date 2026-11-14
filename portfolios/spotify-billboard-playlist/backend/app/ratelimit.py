"""キー（利用者）ごとのスライディングウィンドウ方式の回数制限。メモリ内で動く。"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable

CHART_RATE_LIMIT = 10  # /api/charts を利用者ごとに CHART_RATE_WINDOW 秒あたり何回まで許すか
CHART_RATE_WINDOW = 60.0


class RateLimiter:
    def __init__(
        self, limit: int, window: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._limit = limit
        self._window = window
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """許可するなら呼び出しを記録して True、上限を超えていれば False を返す。"""
        now = self._clock()
        with self._lock:
            # 期限切れの記録を捨て、空になったキーは消す（キー数が増え続けないように）
            for k in list(self._hits):
                hits = self._hits[k]
                while hits and now - hits[0] >= self._window:
                    hits.popleft()
                if not hits:
                    del self._hits[k]
            hits = self._hits.setdefault(key, deque())
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True
