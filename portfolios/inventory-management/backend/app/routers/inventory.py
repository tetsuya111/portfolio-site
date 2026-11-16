"""在庫 API（入出庫の記録・履歴・集計）。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentUser, DbSession
from app.models import MOVEMENT_IN, MOVEMENT_OUT
from app.schemas import HistoryPage, MovementCreate, MovementOut, MovementType, Summary
from app.services.inventory import (
    InsufficientStock,
    ProductNotFound,
    get_summary,
    list_history,
    movement_to_out,
    record_movement,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _record(db, user, data: MovementCreate, movement_type: str) -> MovementOut:
    try:
        movement = record_movement(
            db,
            user=user,
            product_id=data.product_id,
            movement_type=movement_type,
            quantity=data.quantity,
            note=data.note or None,
        )
    except ProductNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="商品が見つかりません。"
        ) from None
    except InsufficientStock as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return movement_to_out(movement)


@router.post(
    "/in", response_model=MovementOut, status_code=status.HTTP_201_CREATED, summary="入庫の記録"
)
def stock_in(data: MovementCreate, db: DbSession, user: CurrentUser) -> MovementOut:
    return _record(db, user, data, MOVEMENT_IN)


@router.post(
    "/out", response_model=MovementOut, status_code=status.HTTP_201_CREATED, summary="出庫の記録"
)
def stock_out(data: MovementCreate, db: DbSession, user: CurrentUser) -> MovementOut:
    return _record(db, user, data, MOVEMENT_OUT)


@router.get("/history", response_model=HistoryPage, summary="入出庫履歴の取得")
def history(
    db: DbSession,
    _user: CurrentUser,
    product_id: int | None = None,
    type: MovementType | None = None,  # noqa: A002  (API のクエリ名)
    date_from: Annotated[date | None, Query(description="開始日（UTC、この日を含む）")] = None,
    date_to: Annotated[date | None, Query(description="終了日（UTC、この日を含む）")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HistoryPage:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="開始日は終了日以前にしてください。",
        )
    items, total = list_history(
        db,
        product_id=product_id,
        movement_type=type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return HistoryPage(
        items=[movement_to_out(m) for m in items], total=total, limit=limit, offset=offset
    )


@router.get("/summary", response_model=Summary, summary="在庫数集計の取得")
def summary(db: DbSession, _user: CurrentUser) -> Summary:
    return get_summary(db)
