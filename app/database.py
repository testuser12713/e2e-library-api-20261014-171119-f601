"""Database engine, session factory and the FastAPI session dependency."""

import os
from collections.abc import Iterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./library.db"


def database_url() -> str:
    """Return the configured database URL, defaulting to a SQLite file next to the app."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


DATABASE_URL = database_url()

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


@event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
    """Enable SQLite foreign-key enforcement for every connection."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Iterator[Session]:
    """Yield a database session and always close it afterwards."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
