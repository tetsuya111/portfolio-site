import pytest
from sqlalchemy import func, select

from app.models import StockMovement
from tests.factories import auth_headers, create_product, create_user


@pytest.fixture
def headers(client, db_session):
    create_user(db_session, username="staff1")
    return auth_headers(client, "staff1")


def move(client, headers, kind, product_id, quantity, note=None):
    body = {"product_id": product_id, "quantity": quantity}
    if note is not None:
        body["note"] = note
    return client.post(f"/inventory/{kind}", json=body, headers=headers)


def stock_of(client, headers, product_id):
    return client.get(f"/products/{product_id}", headers=headers).json()["stock"]


def count_movements(db_session):
    return db_session.scalar(select(func.count(StockMovement.id)))


def test_in_increases_stock(client, db_session, headers):
    product = create_product(db_session)
    res = move(client, headers, "in", product.id, 10)
    assert res.status_code == 201
    assert res.json()["type"] == "in"
    assert res.json()["stock_after"] == 10
    assert stock_of(client, headers, product.id) == 10


def test_out_decreases_stock(client, db_session, headers):
    product = create_product(db_session)
    move(client, headers, "in", product.id, 10)
    res = move(client, headers, "out", product.id, 4)
    assert res.status_code == 201
    assert res.json()["stock_after"] == 6
    assert stock_of(client, headers, product.id) == 6


def test_out_all_stock_to_zero(client, db_session, headers):
    product = create_product(db_session)
    move(client, headers, "in", product.id, 5)
    assert move(client, headers, "out", product.id, 5).status_code == 201
    assert stock_of(client, headers, product.id) == 0


def test_out_exceeding_stock_409_and_unchanged(client, db_session, headers):
    product = create_product(db_session)
    move(client, headers, "in", product.id, 3)
    before = count_movements(db_session)
    res = move(client, headers, "out", product.id, 4)
    assert res.status_code == 409
    assert stock_of(client, headers, product.id) == 3
    assert count_movements(db_session) == before


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "3", 1_000_001, None])
@pytest.mark.parametrize("kind", ["in", "out"])
def test_quantity_invalid_422(client, db_session, headers, kind, quantity):
    product = create_product(db_session)
    assert move(client, headers, kind, product.id, quantity).status_code == 422


def test_quantity_upper_bound_accepted(client, db_session, headers):
    product = create_product(db_session)
    assert move(client, headers, "in", product.id, 1_000_000).status_code == 201


@pytest.mark.parametrize("kind", ["in", "out"])
def test_movement_on_deleted_product_404(client, db_session, headers, kind):
    product = create_product(db_session, stock=5, is_deleted=True)
    assert move(client, headers, kind, product.id, 1).status_code == 404
    assert count_movements(db_session) == 0


@pytest.mark.parametrize("kind", ["in", "out"])
def test_movement_on_missing_product_404(client, headers, kind):
    assert move(client, headers, kind, 9999, 1).status_code == 404


def test_movement_records_user_and_stock_after(client, db_session, headers):
    product = create_product(db_session, sku="A-001", name="ボールペン")
    body = move(client, headers, "in", product.id, 7, note="初回入荷").json()
    assert body["username"] == "staff1"
    assert body["product_sku"] == "A-001"
    assert body["product_name"] == "ボールペン"
    assert body["quantity"] == 7
    assert body["stock_after"] == 7
    assert body["note"] == "初回入荷"
    assert body["created_at"]


def test_note_too_long_422(client, db_session, headers):
    product = create_product(db_session)
    assert move(client, headers, "in", product.id, 1, note="x" * 501).status_code == 422


def test_movements_require_auth_401(client, db_session):
    product = create_product(db_session)
    body = {"product_id": product.id, "quantity": 1}
    assert client.post("/inventory/in", json=body).status_code == 401
    assert client.post("/inventory/out", json=body).status_code == 401
