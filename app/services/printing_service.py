from datetime import date, datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import PRINT_JOB_MAX_ATTEMPTS
from app.database import models
from app.services.order_status_event_service import add_status_event

ACTIVE_PRINT_JOB_STATUSES = ("pending", "printing")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def list_recent_orders(
    db: Session,
    *,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    payment_method: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.Order]:
    stmt = (
        select(models.Order)
        .options(
            joinedload(models.Order.items),
            joinedload(models.Order.print_jobs),
            joinedload(models.Order.status_events),
        )
    )

    if status:
        stmt = stmt.where(models.Order.status == status.strip().lower())

    if payment_method:
        stmt = stmt.where(models.Order.payment_method == payment_method.strip().lower())

    if date_from:
        from_dt = datetime.combine(date_from, datetime.min.time())
        stmt = stmt.where(models.Order.created_at >= from_dt)
    if date_to:
        to_dt = datetime.combine(date_to, datetime.max.time())
        stmt = stmt.where(models.Order.created_at <= to_dt)

    normalized_search = (search or "").strip()
    if normalized_search:
        predicates = [
            models.Order.customer_name.ilike(f"%{normalized_search}%"),
            models.Order.customer_phone.ilike(f"%{normalized_search}%"),
            models.Order.customer_email.ilike(f"%{normalized_search}%"),
        ]
        if normalized_search.isdigit():
            predicates.append(models.Order.id == int(normalized_search))
        stmt = stmt.where(or_(*predicates))

    stmt = stmt.order_by(models.Order.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).unique().all())


def get_order_with_details(db: Session, order_id: int) -> models.Order | None:
    stmt = (
        select(models.Order)
        .options(
            joinedload(models.Order.items),
            joinedload(models.Order.print_jobs),
            joinedload(models.Order.status_events),
        )
        .where(models.Order.id == order_id)
    )
    return db.scalar(stmt)


def get_active_print_job(db: Session, order_id: int) -> models.PrintJob | None:
    stmt = (
        select(models.PrintJob)
        .where(
            models.PrintJob.order_id == order_id,
            models.PrintJob.status.in_(ACTIVE_PRINT_JOB_STATUSES),
        )
        .order_by(models.PrintJob.id.desc())
    )
    return db.scalar(stmt)


def enqueue_print_job(
    db: Session,
    order: models.Order,
    *,
    idempotency_key: str | None = None,
) -> models.PrintJob:
    if idempotency_key:
        existing_by_key = db.scalar(
            select(models.PrintJob).where(models.PrintJob.idempotency_key == idempotency_key)
        )
        if existing_by_key is not None:
            return existing_by_key

    existing_active = get_active_print_job(db, order.id)
    if existing_active is not None:
        return existing_active

    max_attempts = max(1, PRINT_JOB_MAX_ATTEMPTS)
    job = models.PrintJob(
        order_id=order.id,
        status="pending",
        max_attempts=max_attempts,
        idempotency_key=idempotency_key,
    )
    db.add(job)
    db.flush()
    return job


def request_reprint(db: Session, order: models.Order) -> models.PrintJob:
    active_job = get_active_print_job(db, order.id)
    if active_job is not None:
        return active_job

    order.status = "accepted"
    job = models.PrintJob(
        order_id=order.id,
        status="pending",
        max_attempts=max(1, PRINT_JOB_MAX_ATTEMPTS),
    )
    db.add(job)
    db.flush()
    return job


def pull_next_print_job(db: Session, *, agent_id: str) -> models.PrintJob | None:
    stmt = (
        select(models.PrintJob)
        .options(
            joinedload(models.PrintJob.order).joinedload(models.Order.items),
        )
        .where(models.PrintJob.status == "pending")
        .order_by(models.PrintJob.id.asc())
        .limit(1)
    )
    job = db.scalar(stmt)
    if job is None:
        return None

    job.status = "printing"
    job.locked_by = agent_id
    job.attempt_count += 1
    job.updated_at = utc_now()
    job.order.status = "printing"
    add_status_event(
        db,
        order=job.order,
        old_status="accepted",
        new_status="printing",
        source="print_agent",
        note=f"job:{job.id}",
    )
    db.commit()
    db.refresh(job)
    return job


def mark_print_job_completed(db: Session, *, job_id: int, agent_id: str) -> models.PrintJob:
    job = db.get(models.PrintJob, job_id)
    if job is None:
        raise LookupError("Print job not found")

    if job.status == "printed":
        return job

    if job.status != "printing":
        raise ValueError("Print job is not in printing state")

    if job.locked_by and job.locked_by != agent_id:
        raise PermissionError("This print job is currently locked by another agent")

    order = db.get(models.Order, job.order_id)
    if order is None:
        raise LookupError("Order not found for this print job")

    job.status = "printed"
    job.last_error = None
    job.printed_at = utc_now()
    job.updated_at = utc_now()
    order.status = "printed"
    add_status_event(
        db,
        order=order,
        old_status="printing",
        new_status="printed",
        source="print_agent",
        note=f"job:{job.id}",
    )

    db.commit()
    db.refresh(job)
    return job


def mark_print_job_failed(
    db: Session,
    *,
    job_id: int,
    agent_id: str,
    error: str,
) -> models.PrintJob:
    job = db.get(models.PrintJob, job_id)
    if job is None:
        raise LookupError("Print job not found")

    if job.status in {"pending", "failed"}:
        return job

    if job.status != "printing":
        raise ValueError("Print job cannot be marked as failed from its current state")

    if job.locked_by and job.locked_by != agent_id:
        raise PermissionError("This print job is currently locked by another agent")

    order = db.get(models.Order, job.order_id)
    if order is None:
        raise LookupError("Order not found for this print job")

    job.last_error = error.strip()
    job.updated_at = utc_now()

    if job.attempt_count < job.max_attempts:
        job.status = "pending"
        order.status = "accepted"
        add_status_event(
            db,
            order=order,
            old_status="printing",
            new_status="accepted",
            source="print_agent",
            note=f"retry job:{job.id}",
        )
    else:
        job.status = "failed"
        order.status = "failed"
        add_status_event(
            db,
            order=order,
            old_status="printing",
            new_status="failed",
            source="print_agent",
            note=f"failed job:{job.id}",
        )

    db.commit()
    db.refresh(job)
    return job
