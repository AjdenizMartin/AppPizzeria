import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import (
    ALLOWED_PRODUCT_IMAGE_TYPES,
    MAX_PRODUCT_IMAGE_MB,
    PRODUCT_IMAGES_DIR,
)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PRODUCT_IMAGE_BYTES = MAX_PRODUCT_IMAGE_MB * 1024 * 1024


def _validate_upload_file(upload_file: UploadFile) -> str:
    filename = (upload_file.filename or "").strip()
    suffixes = [suffix.lower() for suffix in Path(filename).suffixes]
    if not filename or len(suffixes) != 1 or suffixes[0] not in ALLOWED_EXTENSIONS:
        raise ValueError("Invalid image extension. Allowed: jpg, jpeg, png, webp")

    content_type = (upload_file.content_type or "").strip().lower()
    if content_type not in ALLOWED_PRODUCT_IMAGE_TYPES:
        raise ValueError("Invalid image type. Allowed: image/jpeg, image/png, image/webp")

    upload_file.file.seek(0, 2)
    size = upload_file.file.tell()
    upload_file.file.seek(0)
    if size > MAX_PRODUCT_IMAGE_BYTES:
        raise ValueError(f"Image too large. Max allowed is {MAX_PRODUCT_IMAGE_MB} MB")

    return suffixes[0]


def save_product_image(upload_file: UploadFile) -> str:
    PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    extension = _validate_upload_file(upload_file)
    filename = f"{uuid.uuid4()}{extension}"
    file_path = PRODUCT_IMAGES_DIR / filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return f"/static/images/{filename}"


def delete_product_image(image_url: str | None) -> None:
    if not image_url or not image_url.startswith("/static/images/"):
        return

    image_path = PRODUCT_IMAGES_DIR / image_url.removeprefix("/static/images/")

    if image_path.exists():
        image_path.unlink()
