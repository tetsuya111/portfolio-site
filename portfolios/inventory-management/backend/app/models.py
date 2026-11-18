"""DB のテーブル定義（ER 図は docs/architecture.md）。"""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db import Base

ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"
MOVEMENT_IN = "in"
MOVEMENT_OUT = "out"


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """UTC で保存し、読み込み時に UTC のタイムゾーンを付ける日時型。

    SQLite はタイムゾーンを保存しないため、書き込み時に UTC へ変換して統一する。
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("タイムゾーン付きの日時を指定してください。")
        return value.astimezone(UTC)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'staff')", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False, default=ROLE_STAFF)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utcnow)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
        CheckConstraint("reorder_point >= 0", name="ck_products_reorder_point_non_negative"),
        CheckConstraint(
            "unit_price IS NULL OR unit_price >= 0", name="ck_products_unit_price_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="個")
    unit_price: Mapped[int | None] = mapped_column(Integer)
    reorder_point: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utcnow, onupdate=utcnow
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("type IN ('in', 'out')", name="ck_stock_movements_type"),
        CheckConstraint("quantity > 0", name="ck_stock_movements_quantity_positive"),
        CheckConstraint("stock_after >= 0", name="ck_stock_movements_stock_after_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(3), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_after: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=utcnow, index=True
    )

    product: Mapped[Product] = relationship(lazy="joined")
    user: Mapped[User] = relationship(lazy="joined")
