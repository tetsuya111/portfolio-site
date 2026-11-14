"""DBのセッション。"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

_engine = None
_session_factory = None


def get_engine():
    global _engine, _session_factory
    settings = get_settings()
    url = settings.database_url
    if _engine is None or str(_engine.url) != url:
        kwargs = {"pool_pre_ping": True, "future": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)
    return _engine


def get_session_factory():
    get_engine()
    return _session_factory


@contextmanager
def session_scope():
    """1つの処理の単位でセッションを開く。"""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine():
    """テストでDBを差し替えたときに呼ぶ。"""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
