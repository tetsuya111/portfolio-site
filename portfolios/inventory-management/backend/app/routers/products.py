"""商品マスタ API（CRUD）。削除は論理削除。"""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import AdminUser, CurrentUser, DbSession, EditorUser
from app.models import Product
from app.schemas import ProductIn, ProductOut

router = APIRouter(prefix="/products", tags=["products"])

NOT_FOUND = "商品が見つかりません。"
SKU_TAKEN = "この商品コードは既に使われています（削除済みの商品を含む）。"


def get_active_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return product


def _sku_taken(db: Session, sku: str, exclude_id: int | None = None) -> bool:
    query = select(Product.id).where(Product.sku == sku)
    if exclude_id is not None:
        query = query.where(Product.id != exclude_id)
    return db.scalar(query) is not None


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:  # 同時に同じ商品コードで登録・更新された場合
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SKU_TAKEN) from None


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=list[ProductOut], summary="商品一覧の取得")
def list_products(
    db: DbSession,
    _user: CurrentUser,
    q: str | None = None,
    include_deleted: bool = False,
) -> list[Product]:
    """削除されていない商品を商品コード順に返す。

    include_deleted を指定すると削除済みも含める（履歴の絞り込み用）。
    """
    query = select(Product).order_by(Product.sku)
    if not include_deleted:
        query = query.where(Product.is_deleted.is_(False))
    if q and q.strip():
        pattern = f"%{_escape_like(q.strip())}%"
        query = query.where(
            or_(Product.sku.ilike(pattern, escape="\\"), Product.name.ilike(pattern, escape="\\"))
        )
    return list(db.scalars(query).all())


@router.post(
    "", response_model=ProductOut, status_code=status.HTTP_201_CREATED, summary="商品の登録"
)
def create_product(data: ProductIn, db: DbSession, _user: EditorUser) -> Product:
    if _sku_taken(db, data.sku):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SKU_TAKEN)
    product = Product(**data.model_dump())
    db.add(product)
    _commit_or_conflict(db)
    return product


@router.get("/{product_id}", response_model=ProductOut, summary="商品詳細の取得")
def read_product(product_id: int, db: DbSession, _user: CurrentUser) -> Product:
    return get_active_product(db, product_id)


@router.put("/{product_id}", response_model=ProductOut, summary="商品情報の更新")
def update_product(product_id: int, data: ProductIn, db: DbSession, _user: EditorUser) -> Product:
    product = get_active_product(db, product_id)
    if _sku_taken(db, data.sku, exclude_id=product.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SKU_TAKEN)
    for field, value in data.model_dump().items():
        setattr(product, field, value)
    _commit_or_conflict(db)
    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="商品の削除（管理者のみ・論理削除）",
)
def delete_product(product_id: int, db: DbSession, _admin: AdminUser) -> Response:
    product = get_active_product(db, product_id)
    product.is_deleted = True
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
