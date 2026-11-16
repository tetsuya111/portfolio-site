import pytest
from sqlalchemy import func, select

from app import cli
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
