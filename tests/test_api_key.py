"""Tests for the X-API-Key enforcement on every write endpoint.

The key itself is never written into the repository: the ``auth_headers``
fixture from ``tests/conftest.py`` rolls a per-test key and exposes it through
the test configuration.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Book, Member

VALID_BOOK = {
    "title": "Effective Python",
    "author": "Brett Slatkin",
    "isbn": "978-0-13-485398-7",
    "published_year": 2019,
    "copies": 2,
}

VALID_MEMBER = {"name": "Ada Lovelace", "email": "ada@example.com"}


def _book_count(session: Session) -> int:
    return session.query(Book).count()


def _member_count(session: Session) -> int:
    return session.query(Member).count()


def test_write_without_key_is_unauthorized_and_stores_nothing(
    client: TestClient, db_session: Session
) -> None:
    response = client.post("/books", json=VALID_BOOK)
    assert response.status_code == 401
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "unauthorized"
    assert isinstance(body["error"]["message"], str)
    assert _book_count(db_session) == 0


def test_write_with_wrong_key_is_unauthorized_and_stores_nothing(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/books", json=VALID_BOOK, headers={"X-API-Key": "not-the-configured-key"}
    )
    assert response.status_code == 401
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "unauthorized"
    assert _book_count(db_session) == 0


def test_write_without_configured_key_is_unauthorized(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LIBRARY_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        response = client.post("/books", json=VALID_BOOK, headers={"X-API-Key": "any-value"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert _book_count(db_session) == 0
    finally:
        get_settings.cache_clear()


def test_write_with_configured_key_passes_the_key_check(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post("/books", json=VALID_BOOK, headers=auth_headers)
    assert response.status_code != 401


def test_member_write_with_configured_key_passes_and_without_key_is_rejected(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    rejected = client.post("/members", json=VALID_MEMBER)
    assert rejected.status_code == 401
    assert rejected.json()["error"]["code"] == "unauthorized"
    assert _member_count(db_session) == 0

    allowed = client.post("/members", json=VALID_MEMBER, headers=auth_headers)
    assert allowed.status_code != 401


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/books", VALID_BOOK),
        ("put", "/books/1", VALID_BOOK),
        ("patch", "/books/1", {"title": "Updated"}),
        ("delete", "/books/1", None),
        ("post", "/members", VALID_MEMBER),
        ("put", "/members/1", VALID_MEMBER),
        ("patch", "/members/1", {"name": "Updated"}),
        ("delete", "/members/1", None),
        ("post", "/loans", {"book_id": 1, "member_id": 1}),
        ("post", "/loans/1/return", None),
    ],
)
def test_every_write_endpoint_rejects_a_missing_key(
    client: TestClient, method: str, path: str, payload: dict | None
) -> None:
    request = getattr(client, method)
    response = request(path, json=payload) if payload is not None else request(path)
    assert response.status_code == 401, f"{method.upper()} {path} was not rejected"
    assert response.json()["error"]["code"] == "unauthorized"


def test_read_endpoints_answer_without_any_key(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    assert client.get("/books").status_code != 401
    assert client.get("/members").status_code != 401
    assert client.get("/loans/overdue").status_code != 401


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    """Keep the cached settings from leaking between the tests above."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
