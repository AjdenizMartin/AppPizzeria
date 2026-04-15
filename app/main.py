from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import FRONTEND_DIR, STATIC_DIR
from app.database import models

# DB
from app.database.database import engine, ensure_runtime_schema

models.Base.metadata.create_all(bind=engine)
ensure_runtime_schema()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
app.include_router(api_router)


@app.get("/")
def root():
    return RedirectResponse(url="/app/index.html")
