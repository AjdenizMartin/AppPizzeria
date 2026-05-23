from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(String(1000), nullable=True)
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    customer_name = Column(String(200), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_phone = Column(String(30), nullable=False)
    delivery_address = Column(String(500), nullable=False)
    delivery_city = Column(String(100), nullable=False)
    delivery_postal_code = Column(String(20), nullable=False)
    delivery_notes = Column(String(1000), nullable=True)
    payment_method = Column(String(20), nullable=False, default="card")
    delivery_fee = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(String(50), default="created")
    total_price = Column(Numeric(10, 2))
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    items = relationship("OrderItem", back_populates="order")
    print_jobs = relationship("PrintJob", back_populates="order")
    status_events = relationship(
        "OrderStatusEvent",
        back_populates="order",
        order_by="OrderStatusEvent.created_at.asc()",
    )
    user = relationship("User", back_populates="orders")

    __table_args__ = (Index("ix_orders_status", "status"),)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Numeric(10, 2))
    extras = Column(String(500))
    order = relationship("Order", back_populates="items")


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    last_error = Column(String(1000), nullable=True)
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)
    locked_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    printed_at = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="print_jobs")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    role = Column(String(20), nullable=False, default="customer")
    full_name = Column(String(200), nullable=True)
    address_line = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    orders = relationship("Order", back_populates="user")


class RestaurantSettings(Base):
    __tablename__ = "restaurant_settings"

    id = Column(Integer, primary_key=True, default=1)
    restaurant_name = Column(String(200), nullable=False, default="Pizzeria")
    public_phone = Column(String(50), nullable=False, default="")
    whatsapp_number = Column(String(50), nullable=False, default="")
    address = Column(String(500), nullable=False, default="")
    delivery_fee = Column(Numeric(10, 2), nullable=False, default=0)
    minimum_order_amount = Column(Numeric(10, 2), nullable=False, default=0)
    estimated_delivery_minutes = Column(Integer, nullable=False, default=35)
    is_accepting_orders = Column(Boolean, nullable=False, default=True)
    temporary_closed = Column(Boolean, nullable=False, default=False)
    temporary_closed_message = Column(String(500), nullable=True)
    banner_text = Column(String(500), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class OpeningHour(Base):
    __tablename__ = "opening_hours"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, nullable=False, index=True)
    opens_at = Column(String(5), nullable=False, default="10:00")
    closes_at = Column(String(5), nullable=False, default="22:00")
    is_closed = Column(Boolean, nullable=False, default=False)


class DeliveryZone(Base):
    __tablename__ = "delivery_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    postal_code_prefix = Column(String(20), nullable=False, index=True)
    delivery_fee = Column(Numeric(10, 2), nullable=False, default=0)
    minimum_order_amount = Column(Numeric(10, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)


class OrderStatusEvent(Base):
    __tablename__ = "order_status_events"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source = Column(String(50), nullable=False, default="system")
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    order = relationship("Order", back_populates="status_events")
