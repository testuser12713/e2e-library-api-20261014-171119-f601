"""Loan creation endpoint with the library's lending rules.

An unknown book or member is a 404, a member who already holds the maximum
number of open loans or a book without a free copy is a 409 (and in both
conflict cases no loan row is created), anything else creates the loan.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from ..clock import today
from ..database import get_db
from ..errors import AppError, documented_errors
from ..models import Book, Loan, Member
from ..schemas import LoanCreate, LoanRead
from ..security import require_api_key

router = APIRouter(tags=["loans"])

LOAN_PERIOD_DAYS = 14
MAX_OPEN_LOANS = 3


def _open_loan_count(db: Session, column: ColumnElement[int], value: int) -> int:
    """Count loans that are still open (``returned_at`` is null) for a column."""
    return db.scalar(
        select(func.count()).select_from(Loan).where(column == value, Loan.returned_at.is_(None))
    )


@router.post(
    "/loans",
    response_model=LoanRead,
    status_code=201,
    responses=documented_errors(401, 404, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def create_loan(payload: LoanCreate, db: Session = Depends(get_db)) -> LoanRead:
    """Create a loan from a book to a member, enforcing the lending rules."""
    try:
        book = db.get(Book, payload.book_id)
        if book is None:
            raise AppError(404, "not_found", f"Unknown book_id {payload.book_id}")

        member = db.get(Member, payload.member_id)
        if member is None:
            raise AppError(404, "not_found", f"Unknown member_id {payload.member_id}")

        if _open_loan_count(db, Loan.member_id, member.id) >= MAX_OPEN_LOANS:
            raise AppError(
                409,
                "conflict",
                f"Member {member.id} already holds {MAX_OPEN_LOANS} open loans",
            )

        open_copies = _open_loan_count(db, Loan.book_id, book.id)
        if book.copies - open_copies <= 0:
            raise AppError(
                409,
                "conflict",
                f"Book {book.id} has no free copy available",
            )

        loaned_at = today()
        loan = Loan(
            book_id=book.id,
            member_id=member.id,
            loaned_at=loaned_at,
            due_at=loaned_at + timedelta(days=LOAN_PERIOD_DAYS),
            returned_at=None,
        )
        db.add(loan)
        db.commit()
        db.refresh(loan)
        return loan
    except AppError:
        db.rollback()
        raise
