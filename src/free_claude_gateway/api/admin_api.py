"""Admin API: manage API keys and budgets."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from free_claude_gateway.db.budgets import get_key_usage
from free_claude_gateway.db.database import SessionLocal, authenticate_api_key, create_api_key
from free_claude_gateway.db.models import ApiKey, User

router = APIRouter(prefix="/admin/api", tags=["admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin_key(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
    db: Session = Depends(get_db),
) -> ApiKey:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_api_key:
        token = x_api_key.strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing API key")
    key = authenticate_api_key(db, token)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key


class KeyCreateRequest(BaseModel):
    name: str = Field(default="default", max_length=128)
    max_requests_per_day: int = Field(default=0, ge=0)
    max_tokens_per_day: int = Field(default=0, ge=0)
    max_spend_per_day_usd: float = Field(default=0.0, ge=0)
    max_spend_per_month_usd: float = Field(default=0.0, ge=0)


class KeyUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    is_active: Optional[bool] = None
    max_requests_per_day: Optional[int] = Field(default=None, ge=0)
    max_tokens_per_day: Optional[int] = Field(default=None, ge=0)
    max_spend_per_day_usd: Optional[float] = Field(default=None, ge=0)
    max_spend_per_month_usd: Optional[float] = Field(default=None, ge=0)


def _key_to_dict(key: ApiKey, usage: dict | None = None) -> dict:
    data = {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "is_active": key.is_active,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "max_requests_per_day": key.max_requests_per_day,
        "max_tokens_per_day": key.max_tokens_per_day,
        "max_spend_per_day_usd": key.max_spend_per_day_usd,
        "max_spend_per_month_usd": key.max_spend_per_month_usd,
    }
    if usage is not None:
        data["usage"] = usage
    return data


@router.get("/keys")
def list_keys(_auth: ApiKey = Depends(require_admin_key), db: Session = Depends(get_db)):
    keys = db.scalars(select(ApiKey).order_by(ApiKey.id.desc())).all()
    result = []
    for k in keys:
        usage = get_key_usage(db, k.id)
        result.append(_key_to_dict(k, usage))
    return {"keys": result}


@router.post("/keys")
def create_key(body: KeyCreateRequest, _auth: ApiKey = Depends(require_admin_key), db: Session = Depends(get_db)):
    admin = db.scalar(select(User).where(User.username == "admin"))
    if not admin:
        raise HTTPException(status_code=500, detail="Admin user not found")

    raw, key_obj = create_api_key(db, user_id=admin.id, name=body.name)
    key_obj.max_requests_per_day = body.max_requests_per_day
    key_obj.max_tokens_per_day = body.max_tokens_per_day
    key_obj.max_spend_per_day_usd = body.max_spend_per_day_usd
    key_obj.max_spend_per_month_usd = body.max_spend_per_month_usd
    db.commit()
    db.refresh(key_obj)

    return {
        "key": _key_to_dict(key_obj),
        "raw_key": raw,
        "warning": "Save this key now. It will not be shown again.",
    }


@router.patch("/keys/{key_id}")
def update_key(key_id: int, body: KeyUpdateRequest, _auth: ApiKey = Depends(require_admin_key), db: Session = Depends(get_db)):
    key = db.get(ApiKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    if body.name is not None:
        key.name = body.name
    if body.is_active is not None:
        key.is_active = body.is_active
    if body.max_requests_per_day is not None:
        key.max_requests_per_day = body.max_requests_per_day
    if body.max_tokens_per_day is not None:
        key.max_tokens_per_day = body.max_tokens_per_day
    if body.max_spend_per_day_usd is not None:
        key.max_spend_per_day_usd = body.max_spend_per_day_usd
    if body.max_spend_per_month_usd is not None:
        key.max_spend_per_month_usd = body.max_spend_per_month_usd

    db.commit()
    db.refresh(key)
    usage = get_key_usage(db, key.id)
    return {"key": _key_to_dict(key, usage)}


@router.delete("/keys/{key_id}")
def revoke_key(key_id: int, _auth: ApiKey = Depends(require_admin_key), db: Session = Depends(get_db)):
    key = db.get(ApiKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    key.is_active = False
    db.commit()
    return {"ok": True, "id": key_id, "is_active": False}
