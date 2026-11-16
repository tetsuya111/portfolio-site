"""同じ商品への同時出庫で在庫数がマイナスにならないこと（REQ-INV-6）。"""

import threading

from sqlalchemy import func, select

from app.models import MOVEMENT_OUT, Product, StockMovement
from app.services.inventory import InsufficientStock, record_movement
from tests.factories import create_product, create_user

THREADS = 8
INITIAL_STOCK = 10
QUANTITY = 3


def test_concurrent_outs_never_negative(session_factory, db_session):
    user = create_user(db_session)
    product = create_product(db_session, stock=INITIAL_STOCK)
    barrier = threading.Barrier(THREADS)
    results: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        with session_factory() as session:
            barrier.wait()
            try:
                record_movement(
                    session,
                    user=session.get(type(user), user.id),
                    product_id=product.id,
                    movement_type=MOVEMENT_OUT,
                    quantity=QUANTITY,
                    note=None,
                )
                outcome = "ok"
            except InsufficientStock:
                outcome = "insufficient"
            with lock:
                results.append(outcome)

    threads = [threading.Thread(target=worker) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    db_session.expire_all()
    final_stock = db_session.get(Product, product.id).stock
    out_total = db_session.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.product_id == product.id
        )
    )
    assert len(results) == THREADS
    assert results.count("ok") == INITIAL_STOCK // QUANTITY
    assert final_stock == INITIAL_STOCK - out_total == INITIAL_STOCK % QUANTITY
    assert final_stock >= 0
