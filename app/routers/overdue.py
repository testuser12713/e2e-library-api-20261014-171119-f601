"""Overdue loans endpoint.

Lists the open loans whose due date lies before today. A loan due today is not
overdue and a returned loan never appears. Each entry carries the number of days
it is past due, and the result is paginated.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import clock
from ..database import get_db
from ..errors import documented_errors
from ..models import Loan
from ..schemas import OverdueLoanRead, OverduePage

router = APIRouter(tags=["loans"])


@router.get("/loans/overdue", response_model=OverduePage, responses=documented_errors(422))
def list_overdue_loans(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> OverduePage:
    """Return a page of open loans due before today, oldest due date first."""
    today = clock.today()

    base_filter = (Loan.returned_at.is_(None), Loan.due_at < today)

    total = db.scalar(select(func.count()).select_from(Loan).where(*base_filter)) or 0

    loans = db.scalars(
        select(Loan).where(*base_filter).order_by(Loan.due_at, Loan.id).limit(limit).offset(offset)
    ).all()

    items = [
        OverdueLoanRead(
            book_id=loan.book_id,
            member_id=loan.member_id,
            loaned_at=loan.loaned_at,
            due_at=loan.due_at,
            days_overdue=(today - loan.due_at).days,
        )
        for loan in loans
    ]

    return OverduePage(items=items, total=total, limit=limit, offset=offset)
