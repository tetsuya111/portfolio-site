"""運用コマンド。

python -m app.cli create-admin --username admin --password <8文字以上>
python -m app.cli seed-demo   # デモ用のユーザー・商品・入出庫（既にあれば何もしない）
"""

import argparse
import getpass
import os
import sys
from collections.abc import Sequence

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import make_engine, make_session_factory
from app.models import MOVEMENT_IN, MOVEMENT_OUT, ROLE_VISITOR, Product, User
from app.schemas import UserCreate
from app.services.inventory import record_movement
from app.services.users import UsernameTaken, create_user

ADMIN_PASSWORD_ENV = "INVENTORY_ADMIN_PASSWORD"  # noqa: S105  (環境変数名)
DEMO_PASSWORD = "demo-password"  # noqa: S105  (公開デモ用。README に記載)
DEMO_VISITOR = "demo-visitor"  # 閲覧者。入出庫できないため DEMO_USERS とは分ける
DEMO_USERS = [("demo-admin", "admin"), ("demo-staff", "staff")]  # 入出庫記録の担当者にもなる
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


def _admin_password(cli_value: str | None) -> str:
    if cli_value:
        return cli_value
    from_env = os.environ.get(ADMIN_PASSWORD_ENV)
    if from_env:
        return from_env
    return getpass.getpass("管理者のパスワード（8文字以上）: ")


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


def _add_demo_visitor(db: Session) -> User:
    user = create_user(
        db, UserCreate(username=DEMO_VISITOR, password=DEMO_PASSWORD, role=ROLE_VISITOR)
    )
    print(f"閲覧者 {DEMO_VISITOR} を追加しました。")
    return user


def _seed_demo(db: Session) -> int:
    """デモデータを作る。書き込む前にすべての前提を確認し、途中で失敗して半端に残らないようにする。"""
    visitor = db.scalar(select(User).where(User.username == DEMO_VISITOR))
    if visitor is not None and visitor.role != ROLE_VISITOR:
        # 公開してよい閲覧者のつもりで、書き込みできるアカウントを共有させないため。
        print(
            f"ユーザー {DEMO_VISITOR} が閲覧者以外の権限で存在するため作成しません。",
            file=sys.stderr,
        )
        return 1
    demo_names = [name for name, _ in DEMO_USERS]
    if db.scalar(select(User.id).where(User.username.in_(demo_names))) is not None:
        print("デモデータは作成済みです。")
        # 閲覧者の追加前に作成済みのデモ環境へ、閲覧者だけを足す（商品・入出庫は作らない）。
        if visitor is None:
            _add_demo_visitor(db)
        return 0
    demo_skus = [sku for sku, *_ in DEMO_PRODUCTS]
    taken = db.scalars(select(Product.sku).where(Product.sku.in_(demo_skus))).all()
    if taken:
        # 実際の商品（削除済みを含む）の在庫をデモの入出庫で動かさないため、作成しない。
        print(
            f"デモ用の商品コードが既に使われているため作成しません: {', '.join(taken)}",
            file=sys.stderr,
        )
        return 1
    users = [
        create_user(db, UserCreate(username=name, password=DEMO_PASSWORD, role=role))
        for name, role in DEMO_USERS
    ]
    if visitor is None:
        _add_demo_visitor(db)
    products: dict[str, Product] = {}
    for sku, name, category, unit, price, reorder in DEMO_PRODUCTS:
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
    admin.add_argument(
        "--password",
        help=(
            "非推奨（シェルの履歴に残る）。"
            f"省略時は環境変数 {ADMIN_PASSWORD_ENV}、なければ入力を求める"
        ),
    )
    seed = sub.add_parser("seed-demo", help="デモ用のユーザー・商品・入出庫を作成する")
    seed.add_argument(
        "--allow-production",
        action="store_true",
        help="本番環境でも作成する（公開デモ用。パスワードが README に載っている点に注意）",
    )
    args = parser.parse_args(argv)

    settings = settings or get_settings()
    if args.command == "seed-demo" and settings.is_production and not args.allow_production:
        print(
            "本番環境ではデモデータを作成しません（公開されたパスワードの管理者ができるため）。"
            "公開デモとして作る場合は --allow-production を付けてください。",
            file=sys.stderr,
        )
        return 1
    engine = make_engine(settings.database_url)
    try:
        with make_session_factory(engine)() as db:
            if args.command == "create-admin":
                return _create_admin(db, args.username, _admin_password(args.password))
            return _seed_demo(db)
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
