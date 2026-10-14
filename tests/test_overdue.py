"""Tests for GET /loans/overdue."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Book, Loan, Member

FIXED_TODAY = date(2024, 6, 15)


@pytest.fixture()
def frozen_today(monkeypatch: pytest.MonkeyPatch) -> date:
    """Pin the application's notion of "today" so the boundary is exact."""
    monkeypatch.setattr("app.clock.today", lambda: FIXED_TODAY)
    return FIXED_TODAY


def _seed_book_and_member(db: Session) -> tuple[Book, Member]:
    book = Book(
        title="Der Prozess",
        author="Franz Kafka",
        isbn="978-3-15-009899-7",
        published_year=1925,
        copies=3,
    )
    member = Member(name="Anna Beispiel", email="anna@example.com", member_since=FIXED_TODAY)
    db.add_all([book, member])
    db.commit()
    return book, member


def _add_loan(
    db: Session,
    book: Book,
    member: Member,
    due_at: date,
    returned_at: date | None = None,
) -> Loan:
    loan = Loan(
        book_id=book.id,
        member_id=member.id,
        loaned_at=due_at - timedelta(days=14),
        due_at=due_at,
        returned_at=returned_at,
    )
    db.add(loan)
    db.commit()
    return loan


def test_overdue_loan_due_yesterday_lists_with_days_overdue_one(
    client: TestClient, db_session: Session, frozen_today: date
) -> None:
    book, member = _seed_book_and_member(db_session)
    _add_loan(db_session, book, member, due_at=frozen_today - timedelta(days=1))

    response = client.get("/loans/overdue")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["book_id"] == book.id
    assert item["member_id"] == member.id
    assert item["days_overdue"] == 1
    assert item["due_at"] == (frozen_today - timedelta(days=1)).isoformat()


def test_loan_due_today_is_not_overdue(
    client: TestClient, db_session: Session, frozen_today: date
) -> None:
    book, member = _seed_book_and_member(db_session)
    _add_loan(db_session, book, member, due_at=frozen_today)

    response = client.get("/loans/overdue")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_returned_loan_is_not_listed(
    client: TestClient, db_session: Session, frozen_today: date
) -> None:
    book, member = _seed_book_and_member(db_session)
    _add_loan(
        db_session,
        book,
        member,
        due_at=frozen_today - timedelta(days=5),
        returned_at=frozen_today - timedelta(days=2),
    )

    response = client.get("/loans/overdue")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_limit_and_offset_are_respected(
    client: TestClient, db_session: Session, frozen_today: date
) -> None:
    book, member = _seed_book_and_member(db_session)
    _add_loan(db_session, book, member, due_at=frozen_today - timedelta(days=1))
    _add_loan(db_session, book, member, due_at=frozen_today - timedelta(days=2))
    _add_loan(db_session, book, member, due_at=frozen_today - timedelta(days=3))

    response = client.get("/loans/overdue", params={"limit": 2, "offset": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2
    assert [item["days_overdue"] for item in body["items"]] == [2, 1]


def test_invalid_pagination_is_rejected(client: TestClient, frozen_today: date) -> None:
    response = client.get("/loans/overdue", params={"limit": 0})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
