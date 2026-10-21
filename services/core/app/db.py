from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 10}


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """SQLite возвращает время без часового пояса; приводим всё к UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)
