from fastapi import APIRouter

from app.routers import auth, ops, orders, payments, print_agent, products

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(print_agent.router)
api_router.include_router(ops.router)
