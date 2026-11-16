"""テスト用のデータ作成ヘルパー。"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Product, User
from app.security import hash_password


def create_user(
    db: Session,
    username: str = "alice",
    password: str = "password123",
    role: str = "staff",
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    return user


def create_product(db: Session, sku: str = "A-001", name: str = "テスト商品", **kwargs) -> Product:
    product = Product(sku=sku, name=name, **kwargs)
    db.add(product)
    db.commit()
    return product


def login(client: TestClient, username: str = "alice", password: str = "password123"):
    return client.post("/auth/login", data={"username": username, "password": password})


def auth_headers(
    client: TestClient, username: str = "alice", password: str = "password123"
) -> dict[str, str]:
    res = login(client, username, password)
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
