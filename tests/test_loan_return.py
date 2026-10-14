"""Tests for POST /loans/{loan_id}/return.

The fixtures seed their own Book, Member and open Loan rows directly through the
ORM, so this slice does not depend on the loan-creation endpoint.
"""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.models import Book, Loan, Member


@pytest.fixture()
def seeded_loan(db_session: Session) -> Loan:
    """Seed a book with one copy, a member and an open loan for that book."""
    book = Book(
        title="Der Process",
        author="Franz Kafka",
        isbn="978-3-15-009541-4",
        published_year=1925,
        copies=1,
    )
    member = Member(name="Ada Lovelace", email="ada@example.com", member_since=date(2024, 1, 1))
    db_session.add_all([book, member])
    db_session.commit()
    db_session.refresh(book)
    db_session.refresh(member)

    loan = Loan(
        book_id=book.id,
        member_id=member.id,
        loaned_at=date(2024, 5, 1),
        due_at=date(2024, 5, 15),
        returned_at=None,
    )
    db_session.add(loan)
    db_session.commit()
    db_session.refresh(loan)
    return loan


def _open_loans(db_session: Session, book_id: int) -> int:
    return (
        db_session.query(Loan).filter(Loan.book_id == book_id, Loan.returned_at.is_(None)).count()
    )


def test_return_sets_returned_at_to_today(
    client, auth_headers, seeded_loan: Loan, monkeypatch
) -> None:
    fixed_today = date(2024, 6, 1)
    monkeypatch.setattr("app.routers.loan_returns.today", lambda: fixed_today)

    response = client.post(f"/loans/{seeded_loan.id}/return", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == seeded_loan.id
    assert body["returned_at"] == fixed_today.isoformat()


def test_return_frees_one_copy(
    client, db_session: Session, auth_headers, seeded_loan: Loan
) -> None:
    assert _open_loans(db_session, seeded_loan.book_id) == 1

    response = client.post(f"/loans/{seeded_loan.id}/return", headers=auth_headers)

    assert response.status_code == 200
    assert _open_loans(db_session, seeded_loan.book_id) == 0


def test_second_return_conflicts(client, auth_headers, seeded_loan: Loan) -> None:
    assert client.post(f"/loans/{seeded_loan.id}/return", headers=auth_headers).status_code == 200

    second = client.post(f"/loans/{seeded_loan.id}/return", headers=auth_headers)

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


def test_unknown_loan_id_returns_404(client, auth_headers) -> None:
    response = client.post("/loans/999999/return", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
