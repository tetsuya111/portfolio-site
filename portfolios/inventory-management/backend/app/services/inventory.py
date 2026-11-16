"""在庫の増減・履歴・集計のロジック。

在庫数の整合性は「条件付き UPDATE」で担保する。出庫は
``UPDATE products SET stock = stock - :q WHERE id = :id AND stock >= :q`` の1文で
判定と減算を同時に行うため、同時に出庫が来ても DB が1件ずつ適用し、
在庫が足りない方は0行更新（= 在庫不足）になる。UPDATE と記録の INSERT は同じトランザクション。
"""

import logging
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import MOVEMENT_IN, MOVEMENT_OUT, Product, StockMovement, User, utcnow
from app.schemas import MovementOut

logger = logging.getLogger(__name__)


class ProductNotFound(Exception):
    pass


class InsufficientStock(Exception):
    def __init__(self, available: int, requested: int) -> None:
        super().__init__(f"在庫が不足しています（在庫 {available}、出庫 {requested}）。")
        self.available = available
        self.requested = requested


def record_movement(
    db: Session,
    *,
    user: User,
    product_id: int,
    movement_type: Literal["in", "out"],
    quantity: int,
    note: str | None,
) -> StockMovement:
    """入庫・出庫を記録し、在庫数を増減する。失敗時は何も変更しない。"""
    if movement_type not in (MOVEMENT_IN, MOVEMENT_OUT):
        raise ValueError(f"unknown movement type: {movement_type}")
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    active = (Product.id == product_id) & Product.is_deleted.is_(False)
    try:
        if movement_type == MOVEMENT_IN:
            stmt = update(Product).where(active).values(stock=Product.stock + quantity)
        else:
            stmt = (
                update(Product)
                .where(active, Product.stock >= quantity)
                .values(stock=Product.stock - quantity)
            )
        stmt = stmt.values(updated_at=utcnow()).execution_options(synchronize_session=False)
        updated = db.execute(stmt).rowcount

        if updated == 0:
            current = db.scalar(select(Product.stock).where(active))
            db.rollback()
            if current is None:
                raise ProductNotFound(product_id)
            logger.warning(
                "在庫不足で出庫を拒否しました: product_id=%s stock=%s quantity=%s user=%s",
                product_id,
                current,
                quantity,
                user.username,
            )
            raise InsufficientStock(available=current, requested=quantity)

        stock_after = db.scalar(select(Product.stock).where(Product.id == product_id))
        movement = StockMovement(
            product_id=product_id,
            user_id=user.id,
            type=movement_type,
            quantity=quantity,
            stock_after=stock_after,
            note=note,
        )
        db.add(movement)
        db.commit()
    except (ProductNotFound, InsufficientStock):
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(movement)
    return movement


def movement_to_out(movement: StockMovement) -> MovementOut:
    return MovementOut(
        id=movement.id,
        product_id=movement.product_id,
        product_sku=movement.product.sku,
        product_name=movement.product.name,
        type=movement.type,
        quantity=movement.quantity,
        stock_after=movement.stock_after,
        note=movement.note,
        user_id=movement.user_id,
        username=movement.user.username,
        created_at=movement.created_at,
    )
