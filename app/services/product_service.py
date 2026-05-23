from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import models
from app.services.file_service import delete_product_image, save_product_image


def list_products(db: Session, include_inactive: bool = False) -> list[models.Product]:
    stmt = select(models.Product)
    if not include_inactive:
        stmt = stmt.where(models.Product.is_active.is_(True))
    return list(db.scalars(stmt.order_by(models.Product.id)).all())


async def create_product(
    db: Session,
    name: str,
    price: float,
    category: str,
    description: str = "",
    is_available: bool = True,
    file=None,
) -> models.Product:
    image_url = save_product_image(file) if file else None

    product = models.Product(
        name=name,
        price=price,
        category=category,
        description=description,
        image_url=image_url,
        is_available=is_available,
        is_active=True,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


async def update_product(
    db: Session,
    product_id: int,
    name: str,
    price: float,
    category: str,
    description: str = "",
    is_available: bool = True,
    is_active: bool = True,
    file=None,
) -> models.Product | None:
    product = db.get(models.Product, product_id)

    if product is None:
        return None

    product.name = name
    product.price = price
    product.category = category
    product.description = description
    product.is_available = is_available
    product.is_active = is_active

    if file is not None:
        new_image_url = save_product_image(file)
        delete_product_image(product.image_url)
        product.image_url = new_image_url

    db.commit()
    db.refresh(product)

    return product


def delete_product(db: Session, product_id: int) -> bool:
    product = db.get(models.Product, product_id)

    if product is None:
        return False

    has_order_history = (
        db.query(models.OrderItem)
        .filter(models.OrderItem.product_id == product.id)
        .first()
        is not None
    )
    if has_order_history:
        product.is_active = False
        product.is_available = False
        db.commit()
        return True

    delete_product_image(product.image_url)
    db.delete(product)
    db.commit()
    return True


def set_product_archived(db: Session, product_id: int, archived: bool) -> models.Product | None:
    product = db.get(models.Product, product_id)
    if product is None:
        return None
    product.is_active = not archived
    if archived:
        product.is_available = False
    db.commit()
    db.refresh(product)
    return product
