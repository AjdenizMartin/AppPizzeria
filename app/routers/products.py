from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin, get_db
from app.schemas.product import ProductDeleteResponse, ProductRead
from app.services.product_service import create_product, delete_product, list_products

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductRead])
def get_products(db: Session = Depends(get_db)):
    return list_products(db)


@router.post(
    "/admin/products",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_endpoint(
    name: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    return await create_product(
        db=db,
        name=name,
        price=price,
        category=category,
        description=description,
        file=file,
    )


@router.delete("/admin/products/{product_id}", response_model=ProductDeleteResponse)
def delete_product_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    deleted = delete_product(db, product_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Deleted"}
