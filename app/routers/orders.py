from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.order import OrderCreate, OrderCreateResponse
from app.services.order_service import create_order

router = APIRouter(tags=["orders"])


@router.post("/orders", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
def create_order_endpoint(payload: OrderCreate, db: Session = Depends(get_db)):
    try:
        return create_order(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
