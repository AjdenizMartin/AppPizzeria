from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_print_agent
from app.core.observability import log_business_event
from app.database import models
from app.schemas.order import PrintJobRead
from app.schemas.printing import (
    PrintAgentJobFailRequest,
    PrintAgentJobResolveRequest,
    PrintAgentPullRequest,
    PrintAgentPullResponse,
)
from app.services.printing_service import (
    mark_print_job_completed,
    mark_print_job_failed,
    pull_next_print_job,
)

router = APIRouter(prefix="/print-agent", tags=["print-agent"])


def _get_daily_order_number(db: Session, order: models.Order) -> int:
    created_date = order.created_at.date()
    start = datetime.combine(created_date, time.min, tzinfo=order.created_at.tzinfo)
    end = start + timedelta(days=1)
    stmt = select(func.count(models.Order.id)).where(
        models.Order.created_at >= start,
        models.Order.created_at < end,
        models.Order.id <= order.id,
    )
    return int(db.scalar(stmt) or 1)


def _build_job_payload(db: Session, job) -> dict:
    subtotal = sum(float(item.price) * item.quantity for item in job.order.items)
    return {
        "job_id": job.id,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "order": {
            "id": job.order.id,
            "daily_order_number": _get_daily_order_number(db, job.order),
            "status": job.order.status,
            "customer_name": job.order.customer_name,
            "customer_email": job.order.customer_email,
            "customer_phone": job.order.customer_phone,
            "delivery_address": job.order.delivery_address,
            "delivery_city": job.order.delivery_city,
            "delivery_postal_code": job.order.delivery_postal_code,
            "delivery_notes": job.order.delivery_notes or "",
            "fulfillment_method": job.order.fulfillment_method,
            "payment_method": job.order.payment_method,
            "subtotal": subtotal,
            "delivery_fee": float(job.order.delivery_fee),
            "total_price": job.order.total_price,
            "created_at": job.order.created_at,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "extras": item.extras or "",
                }
                for item in job.order.items
            ],
        },
    }


@router.post("/jobs/pull", response_model=PrintAgentPullResponse)
def pull_print_job(
    request: Request,
    payload: PrintAgentPullRequest,
    db: Session = Depends(get_db),
    _agent_auth=Depends(require_print_agent),
):
    job = pull_next_print_job(db, agent_id=payload.agent_id.strip())
    if job is None:
        return {"job": None}
    log_business_event(
        event="print_job_pulled",
        request=request,
        order_id=job.order.id,
        print_job_id=job.id,
        status=job.status,
    )
    return {"job": _build_job_payload(db, job)}


@router.post("/jobs/{job_id}/complete", response_model=PrintJobRead)
def complete_print_job(
    request: Request,
    job_id: int,
    payload: PrintAgentJobResolveRequest,
    db: Session = Depends(get_db),
    _agent_auth=Depends(require_print_agent),
):
    try:
        job = mark_print_job_completed(db, job_id=job_id, agent_id=payload.agent_id.strip())
        log_business_event(
            event="print_job_completed",
            request=request,
            order_id=job.order_id,
            print_job_id=job.id,
            status=job.status,
        )
        return job
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/fail", response_model=PrintJobRead)
def fail_print_job(
    request: Request,
    job_id: int,
    payload: PrintAgentJobFailRequest,
    db: Session = Depends(get_db),
    _agent_auth=Depends(require_print_agent),
):
    try:
        job = mark_print_job_failed(
            db,
            job_id=job_id,
            agent_id=payload.agent_id.strip(),
            error=payload.error,
        )
        log_business_event(
            event="print_job_failed",
            request=request,
            order_id=job.order_id,
            print_job_id=job.id,
            status=job.status,
            message=payload.error,
        )
        return job
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
