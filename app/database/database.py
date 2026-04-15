from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

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

    with engine.begin() as connection:
        table_exists = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        ).scalar()

        if table_exists is None:
            return

        rows = connection.execute(text("PRAGMA table_info(users)")).mappings().all()
        existing_columns = {row["name"] for row in rows}

        for column_name, column_type in required_user_columns.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))
