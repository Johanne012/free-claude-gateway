from __future__ import annotations

import hashlib
import secrets
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from free_claude_gateway.db.models import ApiKey, Base, User

DB_PATH = Path.home() / ".config" / "free-claude-gateway" / "gateway.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database ready at {DB_PATH}")

    with SessionLocal() as session:
        admin = session.scalar(select(User).where(User.username == "admin"))
        if not admin:
            admin = User(username="admin", email="admin@localhost", is_admin=True, is_active=True)
            session.add(admin)
            session.commit()
            session.refresh(admin)
            raw_key, key_obj = create_api_key(session, user_id=admin.id, name="default-admin")
            session.commit()
            logger.info(f"Created default admin user. API Key (save it): {raw_key}")


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_api_key(
    session: Session,
    user_id: int,
    name: str = "default",
) -> tuple[str, ApiKey]:
    raw = "fcc_" + secrets.token_urlsafe(32)
    prefix = raw[:12]
    key_obj = ApiKey(
        user_id=user_id,
        key_hash=hash_key(raw),
        key_prefix=prefix,
        name=name,
        is_active=True,
    )
    session.add(key_obj)
    session.flush()
    return raw, key_obj


def authenticate_api_key(session: Session, raw_key: str) -> Optional[ApiKey]:
    if not raw_key:
        return None
    h = hash_key(raw_key)
    key = session.scalar(
        select(ApiKey).where(ApiKey.key_hash == h, ApiKey.is_active == True)  # noqa: E712
    )
    return key
