"""運用コマンド。

python -m app.cli create-admin --username admin --password <8文字以上>
python -m app.cli seed-demo   # デモ用のユーザー・商品・入出庫（既にあれば何もしない）
"""

import argparse
import sys
from collections.abc import Sequence

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import make_engine, make_session_factory
from app.models import MOVEMENT_IN, MOVEMENT_OUT, Product, User
from app.schemas import UserCreate
from app.services.inventory import record_movement
from app.services.users import UsernameTaken, create_user

DEMO_PASSWORD = "demo-password"  # noqa: S105  (公開デモ用。README に記載)
DEMO_USERS = [("demo-admin", "admin"), ("demo-staff", "staff")]
DEMO_PRODUCTS = [
    # sku, name, category, unit, unit_price, reorder_point
    ("ST-001", "ボールペン（黒）", "文具", "本", 120, 50),
    ("ST-002", "ノート A5", "文具", "冊", 180, 30),
    ("ST-003", "クリアファイル", "文具", "枚", 40, 100),
    ("OA-001", "コピー用紙 A4", "OA用品", "箱", 2800, 5),
    ("OA-002", "トナーカートリッジ", "OA用品", "個", 9800, 2),
    ("DR-001", "ミネラルウォーター 500ml", "飲料", "本", 90, 48),
]
# sku, 区分, 数量（上から順に登録する）
DEMO_MOVEMENTS = [
    ("ST-001", MOVEMENT_IN, 300),
    ("ST-002", MOVEMENT_IN, 120),
    ("ST-003", MOVEMENT_IN, 500),
    ("OA-001", MOVEMENT_IN, 20),
    ("OA-002", MOVEMENT_IN, 6),
    ("DR-001", MOVEMENT_IN, 96),
    ("ST-001", MOVEMENT_OUT, 80),
    ("ST-003", MOVEMENT_OUT, 450),
    ("OA-001", MOVEMENT_OUT, 16),
    ("OA-002", MOVEMENT_OUT, 4),
    ("DR-001", MOVEMENT_OUT, 60),
]


def _create_admin(db: Session, username: str, password: str) -> int:
    try:
        create_user(db, UserCreate(username=username, password=password, role="admin"))
    except ValidationError as exc:
        print(f"入力が不正です: {exc.errors()[0]['msg']}", file=sys.stderr)
        return 1
    except UsernameTaken:
        print(f"ユーザー {username} は既に存在します。", file=sys.stderr)
        return 1
    print(f"管理者 {username} を作成しました。")
    return 0


def _seed_demo(db: Session) -> int:
    if db.scalar(select(User.id).where(User.username == DEMO_USERS[0][0])) is not None:
        print("デモデータは作成済みです。")
        return 0
    users = [
        create_user(db, UserCreate(username=name, password=DEMO_PASSWORD, role=role))
        for name, role in DEMO_USERS
    ]
    products: dict[str, Product] = {}
    for sku, name, category, unit, price, reorder in DEMO_PRODUCTS:
        product = db.scalar(select(Product).where(Product.sku == sku))
        if product is None:
            product = Product(
                sku=sku,
                name=name,
                category=category,
                unit=unit,
                unit_price=price,
                reorder_point=reorder,
            )
            db.add(product)
        products[sku] = product
    db.commit()
    for i, (sku, kind, qty) in enumerate(DEMO_MOVEMENTS):
        record_movement(
            db,
            user=users[i % len(users)],
            product_id=products[sku].id,
            movement_type=kind,
            quantity=qty,
            note="デモデータ",
        )
    print("デモデータを作成しました。")
    return 0


def main(argv: Sequence[str] | None = None, settings: Settings | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli", description="在庫管理システムの運用コマンド"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="管理者ユーザーを作成する")
    admin.add_argument("--username", required=True)
    admin.add_argument("--password", required=True)
    sub.add_parser("seed-demo", help="デモ用のユーザー・商品・入出庫を作成する")
    args = parser.parse_args(argv)

    settings = settings or get_settings()
    engine = make_engine(settings.database_url)
    try:
        with make_session_factory(engine)() as db:
            if args.command == "create-admin":
                return _create_admin(db, args.username, args.password)
            return _seed_demo(db)
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
