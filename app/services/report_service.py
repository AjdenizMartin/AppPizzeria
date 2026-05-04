from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.database import models
from app.schemas.report import SalesReportResponse, TopProductSold

REVENUE_STATUSES = {"paid", "accepted", "printing", "printed", "ready", "delivered"}


def _day_bounds(target_date: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target_date, time.min).replace(tzinfo=timezone.utc)
    end = datetime.combine(target_date, time.max).replace(tzinfo=timezone.utc)
    return start, end


def get_daily_sales_report(db: Session, *, target_date: date) -> SalesReportResponse:
    start_dt, end_dt = _day_bounds(target_date)

    day_orders = list(
        db.scalars(
            select(models.Order).where(
                and_(models.Order.created_at >= start_dt, models.Order.created_at <= end_dt)
            )
        ).all()
    )

    total_orders = len(day_orders)
    cancelled_orders = sum(1 for order in day_orders if (order.status or "").lower() == "cancelled")

    revenue_orders = [
        order for order in day_orders if (order.status or "").lower() in REVENUE_STATUSES
    ]
    paid_or_completed_orders = len(revenue_orders)

    revenue_total = sum(
        (Decimal(str(order.total_price or 0)) for order in revenue_orders),
        Decimal("0"),
    )
    cash_total = sum(
        (
            Decimal(str(order.total_price or 0))
            for order in revenue_orders
            if (order.payment_method or "").lower() == "cash"
        ),
        Decimal("0"),
    )
    card_total = sum(
        (
            Decimal(str(order.total_price or 0))
            for order in revenue_orders
            if (order.payment_method or "").lower() == "card"
        ),
        Decimal("0"),
    )
    average_ticket = (
        revenue_total / paid_or_completed_orders
        if paid_or_completed_orders
        else Decimal("0")
    )

    top_rows = db.execute(
        select(
            models.OrderItem.product_id,
            func.max(models.OrderItem.product_name).label("product_name"),
            func.sum(models.OrderItem.quantity).label("quantity_sold"),
            func.sum(models.OrderItem.price * models.OrderItem.quantity).label("revenue"),
        )
        .join(models.Order, models.Order.id == models.OrderItem.order_id)
        .where(
            and_(
                models.Order.created_at >= start_dt,
                models.Order.created_at <= end_dt,
                models.Order.status.in_(REVENUE_STATUSES),
            )
        )
        .group_by(models.OrderItem.product_id)
        .order_by(
            func.sum(models.OrderItem.quantity).desc(),
            func.max(models.OrderItem.product_name),
        )
        .limit(10)
    ).all()

    top_products = [
        TopProductSold(
            product_id=int(row.product_id),
            product_name=str(row.product_name),
            quantity_sold=int(row.quantity_sold or 0),
            revenue=float(row.revenue or 0),
        )
        for row in top_rows
    ]
    total_items_sold = sum(item.quantity_sold for item in top_products)

    return SalesReportResponse(
        date=target_date,
        total_orders=total_orders,
        paid_or_completed_orders=paid_or_completed_orders,
        cancelled_orders=cancelled_orders,
        revenue_total=float(revenue_total),
        cash_total=float(cash_total),
        card_total=float(card_total),
        average_ticket=float(average_ticket),
        total_items_sold=total_items_sold,
        top_products=top_products,
    )
