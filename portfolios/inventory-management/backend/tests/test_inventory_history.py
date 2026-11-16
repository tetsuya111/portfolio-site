from datetime import UTC, datetime

import pytest

from app.models import StockMovement
from tests.factories import auth_headers, create_product, create_user


@pytest.fixture
def setup(client, db_session):
    user = create_user(db_session, username="staff1")
    headers = auth_headers(client, "staff1")
    return user, headers


def add_movement(db, user, product, kind, qty, when):
    m = StockMovement(
        product_id=product.id,
        user_id=user.id,
        type=kind,
        quantity=qty,
        stock_after=qty,
        created_at=when,
    )
    db.add(m)
    db.commit()
    return m


def history(client, headers, **params):
    return client.get("/inventory/history", params=params, headers=headers)


def test_history_newest_first_with_names(client, db_session, setup):
    user, headers = setup
    product = create_product(db_session, sku="A-001", name="ボールペン")
    client.post("/inventory/in", json={"product_id": product.id, "quantity": 5}, headers=headers)
    client.post("/inventory/out", json={"product_id": product.id, "quantity": 2}, headers=headers)
    res = history(client, headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert body["limit"] == 20
    assert body["offset"] == 0
    first = body["items"][0]
    assert first["type"] == "out"
    assert first["product_sku"] == "A-001"
    assert first["product_name"] == "ボールペン"
    assert first["username"] == "staff1"
    assert first["stock_after"] == 3


def test_history_filter_product_and_type(client, db_session, setup):
    user, headers = setup
    a = create_product(db_session, sku="A")
    b = create_product(db_session, sku="B")
    now = datetime.now(UTC)
    add_movement(db_session, user, a, "in", 1, now)
    add_movement(db_session, user, a, "out", 1, now)
    add_movement(db_session, user, b, "in", 1, now)
    body = history(client, headers, product_id=a.id, type="in").json()
    assert body["total"] == 1
    assert body["items"][0]["product_id"] == a.id
    assert body["items"][0]["type"] == "in"


def test_history_filter_date_range_inclusive(client, db_session, setup):
    user, headers = setup
    p = create_product(db_session)
    add_movement(db_session, user, p, "in", 1, datetime(2026, 1, 9, 23, 59, tzinfo=UTC))
    add_movement(db_session, user, p, "in", 2, datetime(2026, 1, 10, 0, 0, tzinfo=UTC))
    add_movement(db_session, user, p, "in", 3, datetime(2026, 1, 11, 23, 59, 59, tzinfo=UTC))
    add_movement(db_session, user, p, "in", 4, datetime(2026, 1, 12, 0, 0, tzinfo=UTC))
    body = history(client, headers, date_from="2026-01-10", date_to="2026-01-11").json()
    assert sorted(i["quantity"] for i in body["items"]) == [2, 3]


def test_history_date_from_after_date_to_422(client, setup):
    _, headers = setup
    res = history(client, headers, date_from="2026-01-12", date_to="2026-01-11")
    assert res.status_code == 422


def test_history_pagination_total(client, db_session, setup):
    user, headers = setup
    p = create_product(db_session)
    for i in range(5):
        add_movement(db_session, user, p, "in", i + 1, datetime(2026, 1, 1, i, tzinfo=UTC))
    body = history(client, headers, limit=2, offset=2).json()
    assert body["total"] == 5
    assert [i["quantity"] for i in body["items"]] == [3, 2]


@pytest.mark.parametrize(
    "params", [{"limit": 101}, {"limit": 0}, {"offset": -1}, {"type": "move"}, {"date_from": "x"}]
)
def test_history_invalid_params_422(client, setup, params):
    _, headers = setup
    assert history(client, headers, **params).status_code == 422


def test_history_includes_deleted_product(client, db_session, setup):
    user, headers = setup
    p = create_product(db_session, is_deleted=True)
    add_movement(db_session, user, p, "in", 1, datetime.now(UTC))
    assert history(client, headers).json()["total"] == 1


def test_history_requires_auth_401(client):
    assert client.get("/inventory/history").status_code == 401


def test_history_date_range_uses_utc_offset(client, db_session, setup):
    """JST（UTC+9）の利用者が選んだ日付は、JST の0時〜24時で絞り込む。"""
    user, headers = setup
    p = create_product(db_session)
    # JST 01-10 08:00（UTC 01-09 23:00）は含み、JST 01-11 08:30（UTC 01-10 23:30）は含まない
    add_movement(db_session, user, p, "in", 1, datetime(2026, 1, 9, 14, 59, tzinfo=UTC))
    add_movement(db_session, user, p, "in", 2, datetime(2026, 1, 9, 23, 0, tzinfo=UTC))
    add_movement(db_session, user, p, "in", 3, datetime(2026, 1, 10, 14, 59, tzinfo=UTC))
    add_movement(db_session, user, p, "in", 4, datetime(2026, 1, 10, 23, 30, tzinfo=UTC))
    body = history(
        client, headers, date_from="2026-01-10", date_to="2026-01-10", utc_offset_minutes=540
    ).json()
    assert sorted(i["quantity"] for i in body["items"]) == [2, 3]


@pytest.mark.parametrize("offset", [-841, 841])
def test_history_utc_offset_out_of_range_422(client, setup, offset):
    _, headers = setup
    assert history(client, headers, utc_offset_minutes=offset).status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        {"date_to": "9999-12-31"},
        {"date_from": "0001-01-01", "utc_offset_minutes": 540},
        {"date_from": "9999-12-31", "utc_offset_minutes": -840},
    ],
)
def test_history_extreme_dates_do_not_500(client, db_session, setup, params):
    user, headers = setup
    p = create_product(db_session)
    add_movement(db_session, user, p, "in", 1, datetime(2026, 1, 1, tzinfo=UTC))
    res = history(client, headers, **params)
    assert res.status_code == 200
