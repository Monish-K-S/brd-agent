from collections.abc import Generator
import app.db.models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    # pool_recycle retires connections before the Supabase pooler
    # idle-kills them, so revisits after idle don't pay a reconnect;
    # pre_ping keeps checkouts safe on a transaction-mode pooler.
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Generator:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
