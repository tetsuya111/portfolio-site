import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Product, StockMovement, User


def test_stock_cannot_be_negative(db_session):
    db_session.add(Product(sku="A-1", name="商品", stock=-1))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_sku_unique(db_session):
    db_session.add(Product(sku="A-1", name="商品1"))
    db_session.commit()
    db_session.add(Product(sku="A-1", name="商品2"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_movement_quantity_must_be_positive(db_session):
    user = User(username="alice", password_hash="x", role="staff")
    product = Product(sku="A-1", name="商品")
    db_session.add_all([user, product])
    db_session.commit()
    db_session.add(
        StockMovement(product_id=product.id, user_id=user.id, type="in", quantity=0, stock_after=0)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_role_must_be_known(db_session):
    db_session.add(User(username="bob", password_hash="x", role="owner"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_defaults(db_session):
    product = Product(sku="A-1", name="商品")
    db_session.add(product)
    db_session.commit()
    assert product.stock == 0
    assert product.unit == "個"
    assert product.reorder_point == 0
    assert product.is_deleted is False
    assert product.created_at is not None


def test_visitor_role_is_allowed(db_session):
    db_session.add(User(username="viewer", password_hash="x", role="visitor"))
    db_session.commit()
