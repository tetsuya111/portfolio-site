"""API の入出力スキーマ。"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints, field_validator

from app.security import BCRYPT_MAX_BYTES

Role = Literal["admin", "staff", "visitor"]
MovementType = Literal["in", "out"]

USERNAME_PATTERN = r"^[A-Za-z0-9_-]+$"
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = BCRYPT_MAX_BYTES  # bcrypt が扱える上限
MAX_QUANTITY = 1_000_000


# ---- 認証・ユーザー ----


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int = Field(description="有効期限（秒）")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH)
    role: Role = "staff"

    @field_validator("password")
    @classmethod
    def _password_within_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
            raise ValueError(
                f"パスワードは UTF-8 で {PASSWORD_MAX_BYTES} バイト以内にしてください。"
            )
        return value


# ---- 商品 ----

Trimmed = StringConstraints(strip_whitespace=True)


class ProductIn(BaseModel):
    """商品の登録・更新の入力。在庫数は入出庫でのみ変わるため含めない。"""

    model_config = ConfigDict(extra="ignore")

    sku: Annotated[str, Trimmed, Field(min_length=1, max_length=50)]
    name: Annotated[str, Trimmed, Field(min_length=1, max_length=200)]
    category: Annotated[str, Trimmed, Field(max_length=100)] | None = None
    unit: Annotated[str, Trimmed, Field(min_length=1, max_length=20)] = "個"
    unit_price: Annotated[StrictInt, Field(ge=0)] | None = None
    reorder_point: Annotated[StrictInt, Field(ge=0)] = 0
    description: Annotated[str, Field(max_length=2000)] | None = None

    @field_validator("category", "description")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        return value or None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    category: str | None
    unit: str
    unit_price: int | None
    reorder_point: int
    stock: int
    description: str | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# ---- 入出庫 ----


class MovementCreate(BaseModel):
    product_id: StrictInt
    quantity: Annotated[StrictInt, Field(ge=1, le=MAX_QUANTITY)]
    note: Annotated[str, Field(max_length=500)] | None = None


class MovementOut(BaseModel):
    id: int
    product_id: int
    product_sku: str
    product_name: str
    type: MovementType
    quantity: int
    stock_after: int
    note: str | None
    user_id: int
    username: str
    created_at: datetime


class HistoryPage(BaseModel):
    items: list[MovementOut]
    total: int
    limit: int
    offset: int


class SummaryItem(BaseModel):
    product_id: int
    sku: str
    name: str
    unit: str
    stock: int
    reorder_point: int
    is_low: bool = Field(description="在庫数が発注点以下なら true")


class Summary(BaseModel):
    items: list[SummaryItem]
    total_products: int
    total_stock: int
    low_stock_count: int
