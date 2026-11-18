"""閲覧者（visitor）は参照のみでき、作成・更新・削除はできないこと。"""

import pytest
from sqlalchemy import func, select

from app.models import Product, StockMovement
from tests.factories import auth_headers, create_product, create_user

VISITOR_FORBIDDEN = "閲覧者は操作できません"
PRODUCT_BODY = {"sku": "NEW-001", "name": "新しい商品"}


@pytest.fixture
def product(db_session) -> Product:
    return create_product(db_session, sku="A-001", name="テスト商品", stock=10)


@pytest.fixture
def visitor_headers(client, db_session):
    create_user(db_session, username="viewer", role="visitor")
    return auth_headers(client, "viewer")


@pytest.fixture
def staff_headers(client, db_session):
    create_user(db_session, username="worker", role="staff")
    return auth_headers(client, "worker")


def _count(db_session, model) -> int:
    db_session.expire_all()
    return db_session.scalar(select(func.count(model.id)))


def _assert_forbidden(res) -> None:
    assert res.status_code == 403
    assert res.json()["detail"] == VISITOR_FORBIDDEN


def test_visitor_cannot_create_product(client, db_session, product, visitor_headers):
    _assert_forbidden(client.post("/products", json=PRODUCT_BODY, headers=visitor_headers))
    assert _count(db_session, Product) == 1


def test_visitor_cannot_create_product_with_invalid_body(client, visitor_headers):
    _assert_forbidden(client.post("/products", json={}, headers=visitor_headers))


def test_visitor_cannot_update_product(client, db_session, product, visitor_headers):
    res = client.put(
        f"/products/{product.id}", json={"sku": "A-001", "name": "改名"}, headers=visitor_headers
    )
    _assert_forbidden(res)
    db_session.expire_all()
    assert db_session.get(Product, product.id).name == "テスト商品"


def test_visitor_cannot_update_missing_product(client, visitor_headers):
    _assert_forbidden(client.put("/products/99999", json=PRODUCT_BODY, headers=visitor_headers))


@pytest.mark.parametrize("path", ["/inventory/in", "/inventory/out"])
def test_visitor_cannot_record_movement(client, db_session, product, visitor_headers, path):
    res = client.post(path, json={"product_id": product.id, "quantity": 1}, headers=visitor_headers)
    _assert_forbidden(res)
    db_session.expire_all()
    assert db_session.get(Product, product.id).stock == 10
    assert _count(db_session, StockMovement) == 0


def test_visitor_cannot_delete_product(client, db_session, product, visitor_headers):
    assert client.delete(f"/products/{product.id}", headers=visitor_headers).status_code == 403
    db_session.expire_all()
    assert db_session.get(Product, product.id).is_deleted is False


def test_visitor_cannot_register_user(client, visitor_headers):
    payload = {"username": "intruder", "password": "password123", "role": "admin"}
    assert client.post("/auth/register", json=payload, headers=visitor_headers).status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/products",
        "/products/{id}",
        "/inventory/history",
        "/inventory/summary",
        "/users/me",
    ],
)
def test_visitor_can_read(client, product, visitor_headers, path):
    res = client.get(path.format(id=product.id), headers=visitor_headers)
    assert res.status_code == 200


def test_staff_can_still_write(client, product, staff_headers):
    assert client.post("/products", json=PRODUCT_BODY, headers=staff_headers).status_code == 201
    res = client.post(
        "/inventory/in", json={"product_id": product.id, "quantity": 1}, headers=staff_headers
    )
    assert res.status_code == 201
