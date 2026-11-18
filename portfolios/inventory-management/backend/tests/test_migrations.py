from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

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
