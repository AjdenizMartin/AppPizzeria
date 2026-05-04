from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import DATABASE_URL

_engine_options: dict[str, Any] = {"echo": False}

if DATABASE_URL.startswith("sqlite"):
    _engine_options["connect_args"] = {"check_same_thread": False}

engine: Engine = create_engine(DATABASE_URL, **_engine_options)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


def ensure_runtime_schema() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    required_user_columns = {
        "full_name": "TEXT",
        "address_line": "TEXT",
        "city": "TEXT",
        "postal_code": "TEXT",
        "phone": "TEXT",
    }
    required_order_columns = {
        "user_id": "INTEGER",
        "customer_email": "TEXT",
    }
    required_order_item_columns = {
        "product_name": "TEXT",
    }

    with engine.begin() as connection:
        users_table_exists = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        ).scalar()

        if users_table_exists is not None:
            rows = connection.execute(text("PRAGMA table_info(users)")).mappings().all()
            existing_columns = {row["name"] for row in rows}

            for column_name, column_type in required_user_columns.items():
                if column_name in existing_columns:
                    continue
                sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
                connection.execute(text(sql))

        orders_table_exists = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        ).scalar()
        if orders_table_exists is None:
            return

        order_rows = connection.execute(text("PRAGMA table_info(orders)")).mappings().all()
        existing_order_columns = {row["name"] for row in order_rows}

        for column_name, column_type in required_order_columns.items():
            if column_name in existing_order_columns:
                continue
            connection.execute(text(f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}"))

        order_items_table_exists = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='order_items'")
        ).scalar()
        if order_items_table_exists is None:
            return

        order_item_rows = connection.execute(
            text("PRAGMA table_info(order_items)")
        ).mappings().all()
        existing_order_item_columns = {row["name"] for row in order_item_rows}

        for column_name, column_type in required_order_item_columns.items():
            if column_name in existing_order_item_columns:
                continue
            sql = f"ALTER TABLE order_items ADD COLUMN {column_name} {column_type}"
            connection.execute(text(sql))
