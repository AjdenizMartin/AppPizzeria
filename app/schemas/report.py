from datetime import date

from pydantic import BaseModel


class TopProductSold(BaseModel):
    product_id: int
    product_name: str
    quantity_sold: int
    revenue: float


class SalesReportResponse(BaseModel):
    date: date
    total_orders: int
    paid_or_completed_orders: int
    cancelled_orders: int
    revenue_total: float
    cash_total: float
    card_total: float
    average_ticket: float
    total_items_sold: int
    top_products: list[TopProductSold]
