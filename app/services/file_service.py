import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import PRODUCT_IMAGES_DIR


def save_product_image(upload_file: UploadFile) -> str:
    PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    extension = Path(upload_file.filename or "").suffix
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
