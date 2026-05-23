from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_manager_or_owner
from app.schemas.product import ProductDeleteResponse, ProductRead
from app.services.product_service import (
    create_product,
    delete_product,
    list_products,
    set_product_archived,
    update_product,
)

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductRead])
def get_products(db: Session = Depends(get_db)):
    return list_products(db)


@router.get("/admin/products", response_model=list[ProductRead])
def get_admin_products(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _current_admin=Depends(require_manager_or_owner),
):
    return list_products(db, include_inactive=include_inactive)


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
    is_available: bool = Form(True),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    _current_admin=Depends(require_manager_or_owner),
):
    try:
        return await create_product(
            db=db,
            name=name,
            price=price,
            category=category,
            description=description,
            is_available=is_available,
            file=file,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/admin/products/{product_id}", response_model=ProductDeleteResponse)
def delete_product_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    _current_admin=Depends(require_manager_or_owner),
):
    deleted = delete_product(db, product_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Deleted"}


@router.put("/admin/products/{product_id}", response_model=ProductRead)
async def update_product_endpoint(
    product_id: int,
    name: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    is_available: bool = Form(True),
    is_active: bool = Form(True),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    _current_admin=Depends(require_manager_or_owner),
):
    try:
        updated_product = await update_product(
            db=db,
            product_id=product_id,
            name=name,
            price=price,
            category=category,
            description=description,
            is_available=is_available,
            is_active=is_active,
            file=file,
        )
        if updated_product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return updated_product
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/admin/products/{product_id}/archive", response_model=ProductRead)
def archive_product_endpoint(
    product_id: int,
    archived: bool = Form(True),
    db: Session = Depends(get_db),
    _current_admin=Depends(require_manager_or_owner),
):
    updated = set_product_archived(db, product_id, archived)
    if updated is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated
