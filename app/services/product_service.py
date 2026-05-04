from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import models
from app.services.file_service import delete_product_image, save_product_image


def list_products(db: Session) -> list[models.Product]:
    return list(db.scalars(select(models.Product).order_by(models.Product.id)).all())


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

    delete_product_image(product.image_url)
    db.delete(product)
    db.commit()

    return True
