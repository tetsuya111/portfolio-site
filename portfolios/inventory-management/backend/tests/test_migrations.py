from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["db_url"] = db_url
    return cfg


def test_migration_creates_and_drops_tables(tmp_path):
    url = f"sqlite:///{tmp_path / 'mig.db'}"
    cfg = _config(url)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert {"users", "products", "stock_movements"} <= tables
    command.downgrade(cfg, "base")
    assert not {"users", "products", "stock_movements"} & set(inspect(engine).get_table_names())
    engine.dispose()


def _insert_user(engine, role: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (username, password_hash, role, is_active, created_at) "
                "VALUES (:u, 'x', :r, 1, '2026-01-01 00:00:00')"
            ),
            {"u": f"user-{role}", "r": role},
        )


def test_migration_allows_visitor_role(tmp_path):
    url = f"sqlite:///{tmp_path / 'mig.db'}"
    cfg = _config(url)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    _insert_user(engine, "visitor")
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM users"))
    command.downgrade(cfg, "0001")
    with pytest.raises(IntegrityError):
        _insert_user(engine, "visitor")
    engine.dispose()
