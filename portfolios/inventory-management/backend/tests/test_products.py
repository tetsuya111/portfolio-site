import pytest

from tests.factories import auth_headers, create_product, create_user


@pytest.fixture
def staff(client, db_session):
    create_user(db_session, username="staff1")
    return auth_headers(client, "staff1")


@pytest.fixture
def admin(client, db_session):
    create_user(db_session, username="admin1", role="admin")
    return auth_headers(client, "admin1")


def payload(**kw):
    return {"sku": "A-001", "name": "ボールペン", "category": "文具", "unit": "本"} | kw


def test_create_product_stock_zero(client, staff):
    res = client.post("/products", json=payload(unit_price=120, reorder_point=10), headers=staff)
    assert res.status_code == 201
    body = res.json()
    assert body["stock"] == 0
    assert body["sku"] == "A-001"
    assert body["unit_price"] == 120
    assert body["reorder_point"] == 10
    assert "is_deleted" not in body


def test_create_ignores_stock_in_body(client, staff):
    res = client.post("/products", json=payload(stock=999), headers=staff)
    assert res.status_code == 201
    assert res.json()["stock"] == 0


def test_create_duplicate_sku_409(client, staff):
    assert client.post("/products", json=payload(), headers=staff).status_code == 201
    assert client.post("/products", json=payload(name="別名"), headers=staff).status_code == 409


def test_create_with_deleted_sku_409(client, db_session, staff):
    create_product(db_session, sku="A-001", is_deleted=True)
    assert client.post("/products", json=payload(), headers=staff).status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"sku": "A-001"},
        payload(sku="x" * 51),
        payload(name=""),
        payload(name="   "),
        payload(unit_price=-1),
        payload(reorder_point=-1),
        payload(unit_price="100"),
        payload(unit_price=1.5),
    ],
)
def test_create_invalid_422(client, staff, body):
    assert client.post("/products", json=body, headers=staff).status_code == 422


def test_list_sorted_by_sku_excludes_deleted(client, db_session, staff):
    create_product(db_session, sku="B-001", name="ノート")
    create_product(db_session, sku="A-002", name="消しゴム")
    create_product(db_session, sku="A-001", name="ボールペン", is_deleted=True)
    res = client.get("/products", headers=staff)
    assert res.status_code == 200
    assert [p["sku"] for p in res.json()] == ["A-002", "B-001"]


def test_list_search_q(client, db_session, staff):
    create_product(db_session, sku="PEN-1", name="ボールペン")
    create_product(db_session, sku="NOTE-1", name="ノート")
    create_product(db_session, sku="X-1", name="付箋ペン立て")
    by_sku = client.get("/products", params={"q": "note"}, headers=staff).json()
    assert [p["sku"] for p in by_sku] == ["NOTE-1"]
    by_name = client.get("/products", params={"q": "ペン"}, headers=staff).json()
    assert [p["sku"] for p in by_name] == ["PEN-1", "X-1"]


def test_list_search_treats_wildcards_literally(client, db_session, staff):
    create_product(db_session, sku="A-1", name="100%果汁")
    create_product(db_session, sku="A-2", name="ジュース")
    res = client.get("/products", params={"q": "%"}, headers=staff).json()
    assert [p["sku"] for p in res] == ["A-1"]


def test_get_detail(client, db_session, staff):
    product = create_product(db_session, stock=5)
    res = client.get(f"/products/{product.id}", headers=staff)
    assert res.status_code == 200
    assert res.json()["stock"] == 5


def test_get_missing_and_deleted_404(client, db_session, staff):
    deleted = create_product(db_session, is_deleted=True)
    assert client.get("/products/9999", headers=staff).status_code == 404
    assert client.get(f"/products/{deleted.id}", headers=staff).status_code == 404


def test_update_ignores_stock(client, db_session, staff):
    product = create_product(db_session, stock=7)
    res = client.put(
        f"/products/{product.id}",
        json=payload(sku="A-009", name="新しい名前", stock=100, reorder_point=3),
        headers=staff,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "新しい名前"
    assert body["sku"] == "A-009"
    assert body["reorder_point"] == 3
    assert body["stock"] == 7


def test_update_keeps_own_sku(client, db_session, staff):
    product = create_product(db_session, sku="A-001")
    res = client.put(f"/products/{product.id}", json=payload(name="改名"), headers=staff)
    assert res.status_code == 200


def test_update_duplicate_sku_409(client, db_session, staff):
    create_product(db_session, sku="A-001")
    other = create_product(db_session, sku="A-002")
    res = client.put(f"/products/{other.id}", json=payload(sku="A-001"), headers=staff)
    assert res.status_code == 409


def test_update_missing_404(client, staff):
    assert client.put("/products/9999", json=payload(), headers=staff).status_code == 404


def test_admin_delete_then_404(client, db_session, admin):
    product = create_product(db_session)
    assert client.delete(f"/products/{product.id}", headers=admin).status_code == 204
    assert client.get(f"/products/{product.id}", headers=admin).status_code == 404
    assert client.delete(f"/products/{product.id}", headers=admin).status_code == 404
    assert client.get("/products", headers=admin).json() == []


def test_staff_delete_403(client, db_session, staff):
    product = create_product(db_session)
    assert client.delete(f"/products/{product.id}", headers=staff).status_code == 403
    assert client.get(f"/products/{product.id}", headers=staff).status_code == 200


def test_products_require_auth_401(client, db_session):
    product = create_product(db_session)
    assert client.get("/products").status_code == 401
    assert client.post("/products", json=payload()).status_code == 401
    assert client.get(f"/products/{product.id}").status_code == 401
    assert client.put(f"/products/{product.id}", json=payload()).status_code == 401
    assert client.delete(f"/products/{product.id}").status_code == 401
