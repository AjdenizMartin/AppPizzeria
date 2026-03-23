from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import stripe

from app.database.database import SessionLocal, engine
from app.database import models

# =========================
# CONFIG
# =========================
SECRET_KEY = "sk_test_51TCPtrRvsSTpZ9A47o3zG6XnIEzLSqofaVjlPdB4exXCZfZ63WkKoQDpOCM3xYDDGXVbD7lBDl4GvMPsIFHePry100q8Euii8I"
ALGORITHM = "HS256"

stripe.api_key = "sk_test_51TCPtrRvsSTpZ9A47o3zG6XnIEzLSqofaVjlPdB4exXCZfZ63WkKoQDpOCM3xYDDGXVbD7lBDl4GvMPsIFHePry100q8Euii8I"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI()

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

# =========================
# DB
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================
# AUTH
# =========================
def hash_password(password):
    return pwd_context.hash(password)

def verify_password(p, h):
    return pwd_context.verify(p, h)

def get_user_optional(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    try:
        if credentials:
            token = credentials.credentials
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload["sub"]
    except:
        return None
    return None

# =========================
# ROUTES
# =========================
@app.get("/")
def home():
    return {"message": "API running"}

# =========================
# PRODUCTS
# =========================
@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

# =========================
# ADMIN CRUD PRODUCTS
# =========================
@app.post("/admin/products")
def create_product(data: dict, db: Session = Depends(get_db)):
    product = models.Product(
        name=data["name"],
        description=data.get("description", ""),
        price=data["price"],
        category=data.get("category", "Other")
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.put("/admin/products/{product_id}")
def update_product(product_id: int, data: dict, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()

    if not product:
        raise HTTPException(404)

    product.name = data.get("name", product.name)
    product.price = data.get("price", product.price)
    product.description = data.get("description", product.description)
    product.category = data.get("category", product.category)

    db.commit()

    return {"message": "updated"}


@app.delete("/admin/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()

    if not product:
        raise HTTPException(404)

    db.delete(product)
    db.commit()

    return {"message": "deleted"}

# =========================
# ORDERS
# =========================
@app.post("/orders")
def create_order(user=Depends(get_user_optional), db: Session = Depends(get_db)):
    order = models.Order(status="pending", total_price=0)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@app.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).all()


@app.put("/orders/{order_id}")
def update_order(order_id: int, data: dict, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()

    if not order:
        raise HTTPException(404)

    order.status = data.get("status", order.status)
    db.commit()

    return {"message": "updated"}

# =========================
# STRIPE
# =========================
@app.post("/create-checkout-session")
def create_checkout():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": "Order"},
                    "unit_amount": 2000,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url="http://127.0.0.1:5500/success.html",
            cancel_url="http://127.0.0.1:5500",
        )

        return {"url": session.url}

    except Exception as e:
        return {"error": str(e)}

# =========================
# WEBHOOK
# =========================
@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    print("Webhook received")
    return {"ok": True}