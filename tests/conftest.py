"""Shared fixtures for the library API test suite."""

import secrets
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@pytest.fixture()
def db_engine(tmp_path) -> Iterator[Engine]:
    """A fresh SQLite file with the full schema, isolated per test."""
    from app.database import Base

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine: Engine) -> Iterator[Session]:
    """A session bound to this test's isolated database."""
    testing_session = sessionmaker(
        bind=db_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def api_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Generate a per-test API key and expose it through the test configuration."""
    key = secrets.token_hex(16)
    monkeypatch.setenv("LIBRARY_API_KEY", key)
    get_settings.cache_clear()
    yield key
    get_settings.cache_clear()


@pytest.fixture()
def auth_headers(api_key: str) -> dict[str, str]:
    """Headers carrying a valid API key for the current test configuration."""
    return {"X-API-Key": api_key}


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    """A TestClient whose routes use this test's isolated database session."""
    from app.database import get_db
    from app.main import app

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
