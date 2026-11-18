import pytest
from sqlalchemy import func, select

from app import cli
from app.config import Settings
from app.models import Product, StockMovement, User

pytestmark = pytest.mark.usefixtures("engine")


def test_cli_create_admin(settings, db_session):
    code = cli.main(
        ["create-admin", "--username", "root", "--password", "password123"], settings=settings
    )
    assert code == 0
    user = db_session.scalar(select(User).where(User.username == "root"))
    assert user.role == "admin"


def test_cli_create_admin_duplicate_exits_1(settings):
    args = ["create-admin", "--username", "root", "--password", "password123"]
    assert cli.main(args, settings=settings) == 0
    assert cli.main(args, settings=settings) == 1


def test_cli_create_admin_rejects_short_password(settings):
    args = ["create-admin", "--username", "root", "--password", "short"]
    assert cli.main(args, settings=settings) == 1


def test_cli_seed_demo_idempotent(settings, db_session):
    assert cli.main(["seed-demo"], settings=settings) == 0
    counts = (
        db_session.scalar(select(func.count(User.id))),
        db_session.scalar(select(func.count(Product.id))),
        db_session.scalar(select(func.count(StockMovement.id))),
    )
    assert all(c > 0 for c in counts)
    assert cli.main(["seed-demo"], settings=settings) == 0
    db_session.expire_all()
    assert counts == (
        db_session.scalar(select(func.count(User.id))),
        db_session.scalar(select(func.count(Product.id))),
        db_session.scalar(select(func.count(StockMovement.id))),
    )


def test_cli_create_admin_reads_password_from_env(settings, db_session, monkeypatch):
    monkeypatch.setenv("INVENTORY_ADMIN_PASSWORD", "password123")
    assert cli.main(["create-admin", "--username", "envadmin"], settings=settings) == 0
    assert db_session.scalar(select(User).where(User.username == "envadmin")).role == "admin"


def test_cli_create_admin_prompts_when_no_password(settings, monkeypatch):
    monkeypatch.delenv("INVENTORY_ADMIN_PASSWORD", raising=False)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "password123")
    assert cli.main(["create-admin", "--username", "prompted"], settings=settings) == 0


def test_cli_seed_demo_refuses_existing_demo_sku(settings, db_session):
    db_session.add(Product(sku="ST-001", name="本物の商品", stock=7))
    db_session.commit()
    assert cli.main(["seed-demo"], settings=settings) == 1
    db_session.expire_all()
    assert db_session.scalar(select(func.count(User.id))) == 0
    assert db_session.scalar(select(Product.stock).where(Product.sku == "ST-001")) == 7


def test_cli_seed_demo_skips_when_any_demo_user_exists(settings, db_session):
    from tests.factories import create_user

    create_user(db_session, username="demo-staff")
    assert cli.main(["seed-demo"], settings=settings) == 0
    assert db_session.scalar(select(func.count(Product.id))) == 0


def test_cli_seed_demo_refused_in_production(tmp_path, engine):
    prod = Settings(app_env="production", database_url=str(engine.url), jwt_secret="x" * 40)
    assert cli.main(["seed-demo"], settings=prod) == 1
    assert cli.main(["seed-demo", "--allow-production"], settings=prod) == 0


def test_cli_seed_demo_creates_visitor(settings, db_session):
    assert cli.main(["seed-demo"], settings=settings) == 0
    visitor = db_session.scalar(select(User).where(User.username == "demo-visitor"))
    assert visitor.role == "visitor"
    movement_users = set(db_session.scalars(select(StockMovement.user_id)).all())
    assert movement_users
    assert visitor.id not in movement_users


def test_cli_seed_demo_adds_visitor_when_already_seeded(settings, db_session):
    from tests.factories import create_user

    create_user(db_session, username="demo-staff")
    assert cli.main(["seed-demo"], settings=settings) == 0
    db_session.expire_all()
    visitor = db_session.scalar(select(User).where(User.username == "demo-visitor"))
    assert visitor.role == "visitor"
    assert db_session.scalar(select(func.count(Product.id))) == 0
    assert cli.main(["seed-demo"], settings=settings) == 0
    db_session.expire_all()
    assert db_session.scalar(select(func.count(User.id))) == 2
