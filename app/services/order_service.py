from sqlalchemy.orm import Session

from app.database import models
from app.schemas.order import OrderCreate


def create_order(db: Session, payload: OrderCreate) -> dict[str, float | int]:
    if not payload.items:
        raise ValueError("No items provided")

    order = models.Order(status="pending", total_price=0)
    db.add(order)
    db.flush()

    total = 0.0
    created_items = 0

    for item in payload.items:
        product = db.get(models.Product, item.product_id)

        if product is None:
            continue

        total += product.price * item.quantity
        created_items += 1

        db.add(
            models.OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                price=product.price,
                extras=item.extras,
            )
        )

    if created_items == 0:
        db.rollback()
        raise ValueError("No valid products found")

    order.total_price = total
    db.commit()
    db.refresh(order)

    return {"order_id": order.id, "total": total}
