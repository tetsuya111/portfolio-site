import os
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ.setdefault("BCRYPT_ROUNDS", "4")  # app.security の import 前に設定する
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app import models  # noqa: F401  (テーブル定義を Base に登録する)
from app.config import Settings
from app.db import Base, get_db, make_engine
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        jwt_secret="test-secret-" + "x" * 32,
    )


@pytest.fixture
def engine(settings: Settings):
    eng = make_engine(settings.database_url)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(settings: Settings, session_factory) -> Iterator[TestClient]:
    app = create_app(settings)

    def override_get_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
