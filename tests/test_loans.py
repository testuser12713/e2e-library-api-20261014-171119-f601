"""Tests for POST /loans: the lending rules and the created loan."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import today
from app.models import Book, Loan, Member


def _make_book(db: Session, copies: int, isbn: str = "978-3-16-148410-0") -> Book:
    book = Book(
        title="Effective Python",
        author="Brett Slatkin",
        isbn=isbn,
        published_year=2019,
        copies=copies,
    )
    db.add(book)
    db.commit()
    return book


def _make_member(db: Session, email: str = "ada@example.com") -> Member:
    member = Member(name="Ada Lovelace", email=email)
    db.add(member)
    db.commit()
    return member


def _loan_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Loan))


def test_create_loan_returns_201_with_14_day_due_date(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _make_book(db_session, copies=1)
    member = _make_member(db_session)

    response = client.post(
        "/loans",
        json={"book_id": book.id, "member_id": member.id},
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "book_id", "member_id", "loaned_at", "due_at", "returned_at"}
    assert body["book_id"] == book.id
    assert body["member_id"] == member.id
    assert body["returned_at"] is None

    loaned_at = date.fromisoformat(body["loaned_at"])
    due_at = date.fromisoformat(body["due_at"])
    assert due_at == loaned_at + timedelta(days=14)
    assert loaned_at == today()


def test_third_loan_succeeds_and_fourth_is_rejected(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _make_book(db_session, copies=10)
    member = _make_member(db_session)

    for _ in range(3):
        response = client.post(
            "/loans",
            json={"book_id": book.id, "member_id": member.id},
            headers=auth_headers,
        )
        assert response.status_code == 201

    response = client.post(
        "/loans",
        json={"book_id": book.id, "member_id": member.id},
        headers=auth_headers,
    )
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "conflict"

    assert _loan_count(db_session) == 3


def test_book_with_zero_copies_is_never_borrowable(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _make_book(db_session, copies=0)
    member = _make_member(db_session)

    response = client.post(
        "/loans",
        json={"book_id": book.id, "member_id": member.id},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert _loan_count(db_session) == 0


def test_book_with_all_copies_lent_is_rejected(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    book = _make_book(db_session, copies=1)
    first_member = _make_member(db_session, email="first@example.com")
    second_member = _make_member(db_session, email="second@example.com")

    first = client.post(
        "/loans",
        json={"book_id": book.id, "member_id": first_member.id},
        headers=auth_headers,
    )
    assert first.status_code == 201

    response = client.post(
        "/loans",
        json={"book_id": book.id, "member_id": second_member.id},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert _loan_count(db_session) == 1


@pytest.mark.parametrize("unknown_field", ["book_id", "member_id"])
def test_unknown_book_or_member_returns_404(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
    unknown_field: str,
) -> None:
    book = _make_book(db_session, copies=1)
    member = _make_member(db_session)

    payload = {"book_id": book.id, "member_id": member.id}
    payload[unknown_field] = 99999

    response = client.post("/loans", json=payload, headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert _loan_count(db_session) == 0
