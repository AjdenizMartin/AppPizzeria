from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "app" / "static"
PRODUCT_IMAGES_DIR = STATIC_DIR / "images"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pizzeria.db").strip()
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5500").rstrip("/")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me").strip()
TOKEN_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
STRIPE_KEY = (os.getenv("STRIPE_KEY") or "").strip()
ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", "").split(",")
    if email.strip()
}
