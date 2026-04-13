from fastapi import APIRouter

from app.routers import auth, orders, payments, products

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
