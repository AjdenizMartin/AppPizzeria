from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin, get_db, get_optional_current_user
from app.core.observability import log_business_event
from app.database.models import User
from app.schemas.order import (
    CashCheckoutResponse,
    OrderAdminRead,
    OrderCreate,
    OrderCreateResponse,
    OrderStatusUpdate,
    PrintRequeueResponse,
)
from app.services.order_service import (
    create_cash_checkout_order,
    create_order,
    list_orders,
    requeue_order_print,
    update_order_status,
)

router = APIRouter(tags=["orders"])


@router.post("/orders", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
def create_order_endpoint(
    request: Request,
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        created = create_order(db, payload, current_user=current_user)
        log_business_event(
            event="order_created",
            request=request,
            order_id=int(created["order_id"]),
            status=str(created["status"]),
        )
        return created
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/orders/cash-checkout",
    response_model=CashCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cash_checkout_order_endpoint(
    request: Request,
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        created = create_cash_checkout_order(db, payload, current_user=current_user)
        log_business_event(
            event="order_cash_checkout",
            request=request,
            order_id=int(created["order_id"]),
            payment_method="cash",
            status=str(created["status"]),
        )
        return created
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    request: Request,
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    try:
        updated = update_order_status(db, order_id=order_id, next_status=payload.status)
        log_business_event(
            event="order_status_updated",
            request=request,
            order_id=updated.id,
            status=updated.status,
        )
        return updated
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/admin/orders/{order_id}/reprint", response_model=PrintRequeueResponse)
def reprint_order_endpoint(
    request: Request,
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

    log_business_event(
        event="order_reprint_requested",
        request=request,
        order_id=order.id,
        print_job_id=job.id,
        status=job.status,
    )

    return {
        "order_id": order.id,
        "print_job": job,
    }
