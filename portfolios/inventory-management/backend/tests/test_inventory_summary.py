import random

import pytest
from sqlalchemy import func, select

from app.models import MOVEMENT_IN, MOVEMENT_OUT, Product, StockMovement
from app.services.inventory import InsufficientStock, record_movement
from tests.factories import auth_headers, create_product, create_user


@pytest.fixture
def headers(client, db_session):
    create_user(db_session, username="staff1")
    return auth_headers(client, "staff1")


def summary(client, headers):
    res = client.get("/inventory/summary", headers=headers)
    assert res.status_code == 200
    return res.json()


def test_summary_empty(client, headers):
    assert summary(client, headers) == {
        "items": [],
        "total_products": 0,
        "total_stock": 0,
        "low_stock_count": 0,
    }


def test_summary_counts_and_low_flag(client, db_session, headers):
    create_product(db_session, sku="B", stock=10, reorder_point=10)  # 発注点と同じ → 少ない
    create_product(db_session, sku="A", stock=11, reorder_point=10)
    create_product(db_session, sku="C", stock=0)  # 発注点0・在庫0 → 少ない
    body = summary(client, headers)
    assert [i["sku"] for i in body["items"]] == ["A", "B", "C"]
    assert [i["is_low"] for i in body["items"]] == [False, True, True]
    assert body["total_products"] == 3
    assert body["total_stock"] == 21
    assert body["low_stock_count"] == 2


def test_summary_excludes_deleted(client, db_session, headers):
    create_product(db_session, sku="A", stock=5)
    create_product(db_session, sku="B", stock=7, is_deleted=True)
    body = summary(client, headers)
    assert [i["sku"] for i in body["items"]] == ["A"]
    assert body["total_stock"] == 5


def test_summary_matches_movement_totals(client, db_session, headers):
    user = create_user(db_session, username="worker")
    products = [create_product(db_session, sku=f"P-{i}") for i in range(3)]
    rng = random.Random(42)
    for _ in range(50):
        product = rng.choice(products)
        kind = rng.choice([MOVEMENT_IN, MOVEMENT_OUT])
        try:
            record_movement(
                db_session,
                user=user,
                product_id=product.id,
                movement_type=kind,
                quantity=rng.randint(1, 20),
                note=None,
            )
        except InsufficientStock:
            pass
    db_session.expire_all()  # record_movement の更新を読み直す
    body = summary(client, headers)
    for item in body["items"]:

        def total(kind, pid=item["product_id"]):
            return db_session.scalar(
                select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
                    StockMovement.product_id == pid, StockMovement.type == kind
                )
            )

        assert item["stock"] == total(MOVEMENT_IN) - total(MOVEMENT_OUT)
        assert item["stock"] >= 0
        assert item["stock"] == db_session.get(Product, item["product_id"]).stock


def test_summary_requires_auth_401(client):
    assert client.get("/inventory/summary").status_code == 401
