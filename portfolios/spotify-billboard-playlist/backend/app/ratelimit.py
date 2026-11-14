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
        self._next_sweep = 0.0
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """許可するなら呼び出しを記録して True、上限を超えていれば False を返す。"""
        now = self._clock()
        with self._lock:
            # 普段は呼ばれたキーだけを掃除し、全キーの掃除はウィンドウごとに1回だけ行う
            if now >= self._next_sweep:
                for k in list(self._hits):
                    self._prune(k, now)
                self._next_sweep = now + self._window
            hits = self._hits.setdefault(key, deque())
            self._prune_deque(hits, now)
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True

    def _prune_deque(self, hits: deque[float], now: float) -> None:
        while hits and now - hits[0] >= self._window:
            hits.popleft()

    def _prune(self, key: str, now: float) -> None:
        """期限切れの記録を捨て、空になったキーは消す（ロック内で呼ぶ）。"""
        hits = self._hits[key]
        self._prune_deque(hits, now)
        if not hits:
            del self._hits[key]
