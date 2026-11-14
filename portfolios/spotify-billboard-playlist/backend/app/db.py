"""SQLite によるチャートURL・曲一覧の保存。"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from app.batch.parser import ChartEntry

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chart_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'failed')),
    error TEXT,
    created_at TEXT NOT NULL,
    fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS chart_tracks (
    source_id INTEGER NOT NULL REFERENCES chart_sources(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    PRIMARY KEY (source_id, rank)
);
"""


MAX_SOURCES = 1000  # 保持するチャートURLの件数。超えたら処理済みのものを古い順に削除する


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str, max_sources: int = MAX_SOURCES) -> None:
        self._max_sources = max_sources
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def add_source(self, url: str) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO chart_sources (url, created_at) VALUES (?, ?)", (url, _now())
            )
            # 処理済み（done / failed）のうち古いものを削除する。曲データは ON DELETE CASCADE で
            # 一緒に消える。未処理（pending）は処理中・バッチ待ちのため消さない
            self._conn.execute(
                "DELETE FROM chart_sources WHERE status != 'pending' AND id NOT IN "
                "(SELECT id FROM chart_sources WHERE status != 'pending' ORDER BY id DESC LIMIT ?)",
                (self._max_sources,),
            )
            return int(cur.lastrowid)

    def get_source(self, source_id: int) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM chart_sources WHERE id = ?", (source_id,)
            ).fetchone()
        return dict(row) if row else None

    def pending_ids(self) -> list[int]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id FROM chart_sources WHERE status = 'pending' ORDER BY id"
            ).fetchall()
        return [row["id"] for row in rows]

    def mark_done(self, source_id: int, entries: list[ChartEntry]) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM chart_tracks WHERE source_id = ?", (source_id,))
            self._conn.executemany(
                "INSERT INTO chart_tracks (source_id, rank, title, artist) VALUES (?, ?, ?, ?)",
                [(source_id, e.rank, e.title, e.artist) for e in entries],
            )
            self._conn.execute(
                "UPDATE chart_sources SET status = 'done', error = NULL, fetched_at = ? "
                "WHERE id = ?",
                (_now(), source_id),
            )

    def mark_failed(self, source_id: int, error: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE chart_sources SET status = 'failed', error = ?, fetched_at = ? "
                "WHERE id = ?",
                (error, _now(), source_id),
            )

    def tracks(self, source_id: int) -> list[ChartEntry]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT rank, title, artist FROM chart_tracks WHERE source_id = ? ORDER BY rank",
                (source_id,),
            ).fetchall()
        return [ChartEntry(row["rank"], row["title"], row["artist"]) for row in rows]
