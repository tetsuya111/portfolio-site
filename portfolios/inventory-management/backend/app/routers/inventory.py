"""在庫 API（入出庫の記録・履歴・集計）。"""

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.models import MOVEMENT_IN, MOVEMENT_OUT
from app.schemas import MovementCreate, MovementOut
from app.services.inventory import (
    InsufficientStock,
    ProductNotFound,
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
