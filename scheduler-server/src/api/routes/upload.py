"""文件上传路由。"""
import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from src.api.deps import db_session
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile, db: Session = Depends(db_session)) -> dict:
    content = await file.read()
    ext = Path(file.filename or "file").suffix or ""
    # prevent overwrites by hashing content as suffix
    digest = hashlib.sha256(content).hexdigest()[:12]
    safe_name = f"{uuid.uuid4().hex[:8]}-{digest}{ext}"
    dest = UPLOAD_DIR / safe_name
    dest.write_bytes(content)

    return {
        "url": f"/uploads/{safe_name}",
        "name": file.filename or "file",
        "size": len(content),
        "mime": file.content_type or "application/octet-stream",
    }
