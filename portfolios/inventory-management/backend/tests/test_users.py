import pytest

from tests.factories import auth_headers, create_user, login


@pytest.fixture
def admin_headers(client, db_session):
    create_user(db_session, username="admin", role="admin")
    return auth_headers(client, "admin")


def register(client, headers, **body):
    payload = {"username": "bob", "password": "password123", "role": "staff"} | body
    return client.post("/auth/register", json=payload, headers=headers)


def test_admin_can_register_user_and_user_can_login(client, admin_headers):
    res = register(client, admin_headers)
    assert res.status_code == 201
    assert res.json()["username"] == "bob"
    assert res.json()["role"] == "staff"
    assert login(client, "bob").status_code == 200


def test_register_defaults_to_staff(client, admin_headers):
    res = client.post(
        "/auth/register",
        json={"username": "carol", "password": "password123"},
        headers=admin_headers,
    )
    assert res.status_code == 201
    assert res.json()["role"] == "staff"


def test_staff_cannot_register_403(client, db_session):
    create_user(db_session, username="staff1")
    res = register(client, auth_headers(client, "staff1"))
    assert res.status_code == 403
    assert login(client, "bob").status_code == 401


def test_register_requires_auth_401(client):
    assert register(client, {}).status_code == 401


def test_duplicate_username_409(client, admin_headers):
    assert register(client, admin_headers).status_code == 201
    assert register(client, admin_headers).status_code == 409


@pytest.mark.parametrize("username", ["ab", "a b", "a" * 51, "名前です"])
def test_invalid_username_422(client, admin_headers, username):
    assert register(client, admin_headers, username=username).status_code == 422


def test_short_password_422(client, admin_headers):
    assert register(client, admin_headers, password="1234567").status_code == 422


def test_password_over_72_bytes_422(client, admin_headers):
    assert register(client, admin_headers, password="あ" * 25).status_code == 422


def test_unknown_role_422(client, admin_headers):
    assert register(client, admin_headers, role="owner").status_code == 422


def test_list_users_admin_only(client, db_session, admin_headers):
    create_user(db_session, username="staff1")
    res = client.get("/users", headers=admin_headers)
    assert res.status_code == 200
    assert [u["username"] for u in res.json()] == ["admin", "staff1"]
    assert client.get("/users", headers=auth_headers(client, "staff1")).status_code == 403
