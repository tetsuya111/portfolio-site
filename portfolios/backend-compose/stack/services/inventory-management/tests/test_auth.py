from datetime import UTC, datetime, timedelta

import jwt

from app.security import verify_password
from tests.factories import auth_headers, create_user, login


def test_login_success_returns_token(client, db_session):
    create_user(db_session)
    res = login(client)
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] == 60 * 60


def test_login_wrong_password_and_unknown_user_return_same_401(client, db_session):
    create_user(db_session)
    wrong = login(client, password="wrong-password")
    unknown = login(client, username="nobody")
    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_login_inactive_user_401(client, db_session):
    create_user(db_session, is_active=False)
    assert login(client).status_code == 401


def test_me_returns_user_without_password(client, db_session):
    create_user(db_session, role="admin")
    res = client.get("/users/me", headers=auth_headers(client))
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "alice"
    assert body["role"] == "admin"
    assert "password_hash" not in body
    assert "password" not in body


def test_me_without_token_401(client):
    assert client.get("/users/me").status_code == 401


def test_me_with_expired_token_401(client, db_session, settings):
    user = create_user(db_session)
    past = datetime.now(UTC) - timedelta(hours=2)
    token = jwt.encode(
        {"sub": str(user.id), "role": "staff", "iat": past, "exp": past + timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    res = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_me_with_bad_signature_401(client, db_session):
    user = create_user(db_session)
    token = jwt.encode(
        {"sub": str(user.id), "role": "admin"}, "other-secret" * 4, algorithm="HS256"
    )
    res = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_me_with_unsigned_token_401(client, db_session):
    user = create_user(db_session)
    token = jwt.encode({"sub": str(user.id), "role": "admin"}, None, algorithm="none")
    res = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_token_of_deactivated_user_401(client, db_session):
    user = create_user(db_session)
    headers = auth_headers(client)
    user.is_active = False
    db_session.commit()
    assert client.get("/users/me", headers=headers).status_code == 401


def test_password_is_hashed(db_session):
    user = create_user(db_session, password="password123")
    assert user.password_hash != "password123"
    assert verify_password("password123", user.password_hash)
    assert not verify_password("password124", user.password_hash)
