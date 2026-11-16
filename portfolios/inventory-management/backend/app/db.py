"""DB の接続とセッション。"""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(url: str, **kwargs) -> Engine:
    """エンジンを作る。SQLite では外部キーと busy_timeout を有効にする。"""
    is_sqlite = url.startswith("sqlite")
    connect_args = {"check_same_thread": False, "timeout": 5} if is_sqlite else {}
    engine = create_engine(url, connect_args=connect_args, **kwargs)
    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _record) -> None:  # pragma: no cover - 接続時のみ
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_db(request: Request) -> Iterator[Session]:
    """リクエストごとのセッションを返す（create_app が app.state に置いたファクトリを使う）。"""
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()
