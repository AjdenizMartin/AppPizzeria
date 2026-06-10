from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_db,
    get_optional_current_user,
    require_staff_or_manager_or_owner,
)
from app.core.observability import log_business_event
from app.database.models import User
from app.schemas.order import (
    CashCheckoutResponse,
    OrderAdminRead,
    OrderCreate,
    OrderCreateResponse,
    OrderStatusUpdate,
    OrderTrackingRead,
    PrintRequeueResponse,
)
from app.services.order_service import (
    create_cash_checkout_order,
    create_order,
    get_order_for_tracking,
    list_orders,
    requeue_order_print,
    update_order_status,
)

router = APIRouter(tags=["orders"])


def _timeline_label(status: str) -> str:
    mapping = {
        "created": "Pedido recibido",
        "paid": "Pago confirmado",
        "accepted": "Preparando",
        "printing": "En impresion",
        "printed": "Listo en cocina",
        "ready": "Listo",
        "delivered": "Entregado",
        "cancelled": "Cancelado",
        "failed": "Incidencia",
    }
    return mapping.get(status, status)


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


@router.get("/orders/{order_id}/tracking", response_model=OrderTrackingRead)
def get_order_tracking(
    order_id: int,
    email: str | None = None,
    phone: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        order = get_order_for_tracking(db, order_id=order_id, email=email, phone=phone)
        timeline = [
            {
                "status": event.new_status,
                "label": _timeline_label(event.new_status),
                "created_at": event.created_at,
            }
            for event in order.status_events
        ]
        return {
            "id": order.id,
            "status": order.status,
            "customer_name": order.customer_name,
            "customer_email": order.customer_email,
            "customer_phone": order.customer_phone,
            "delivery_address": order.delivery_address,
            "delivery_city": order.delivery_city,
            "delivery_postal_code": order.delivery_postal_code,
            "delivery_notes": order.delivery_notes,
            "fulfillment_method": order.fulfillment_method,
            "payment_method": order.payment_method,
            "delivery_fee": order.delivery_fee,
            "total_price": order.total_price,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "items": order.items,
            "print_jobs": order.print_jobs,
            "status_events": timeline,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError:
        raise HTTPException(status_code=404, detail="Order not found") from None
    except PermissionError:
        raise HTTPException(status_code=404, detail="Order not found") from None


@router.get("/admin/orders", response_model=list[OrderAdminRead])
def list_orders_endpoint(
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    payment_method: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _current_admin=Depends(require_staff_or_manager_or_owner),
):
    return list_orders(
        db,
        status=status,
        date_from=date_from,
        date_to=date_to,
        search=search,
        payment_method=payment_method,
        limit=limit,
        offset=offset,
    )


@router.patch("/admin/orders/{order_id}/status", response_model=OrderAdminRead)
def update_order_status_endpoint(
    request: Request,
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_staff_or_manager_or_owner),
):
    try:
        updated = update_order_status(
            db,
            order_id=order_id,
            next_status=payload.status,
            changed_by_user_id=current_admin.id,
        )
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
    current_admin: User = Depends(require_staff_or_manager_or_owner),
):
    try:
        order, job = requeue_order_print(
            db,
            order_id=order_id,
            changed_by_user_id=current_admin.id,
        )
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
