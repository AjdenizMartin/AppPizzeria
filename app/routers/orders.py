from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin, get_db
from app.schemas.order import (
    OrderAdminRead,
    OrderCreate,
    OrderCreateResponse,
    OrderStatusUpdate,
    PrintRequeueResponse,
)
from app.services.order_service import (
    create_order,
    list_orders,
    requeue_order_print,
    update_order_status,
)

router = APIRouter(tags=["orders"])


@router.post("/orders", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
def create_order_endpoint(payload: OrderCreate, db: Session = Depends(get_db)):
    try:
        return create_order(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/admin/orders", response_model=list[OrderAdminRead])
def list_orders_endpoint(
    limit: int = 50,
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    safe_limit = min(max(limit, 1), 200)
    return list_orders(db, limit=safe_limit)


@router.patch("/admin/orders/{order_id}/status", response_model=OrderAdminRead)
def update_order_status_endpoint(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    try:
        return update_order_status(db, order_id=order_id, next_status=payload.status)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/admin/orders/{order_id}/reprint", response_model=PrintRequeueResponse)
def reprint_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    try:
        order, job = requeue_order_print(db, order_id=order_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "order_id": order.id,
        "print_job": job,
    }
