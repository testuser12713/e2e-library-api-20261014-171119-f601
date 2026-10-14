"""Loan return endpoint.

Returning an open loan stamps ``returned_at`` with today's date, which frees one
copy of the book: the number of free copies is derived from the open ``Loan``
rows, so no other book state has to be written here.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..clock import today
from ..database import get_db
from ..errors import AppError, documented_errors
from ..models import Loan
from ..schemas import LoanRead
from ..security import require_api_key

router = APIRouter(tags=["loans"])


@router.post(
    "/loans/{loan_id}/return",
    response_model=LoanRead,
    responses=documented_errors(401, 404, 409),
    dependencies=[Depends(require_api_key)],
)
def return_loan(loan_id: int, db: Annotated[Session, Depends(get_db)]) -> Loan:
    """Mark an open loan as returned today and free one copy of its book."""
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise AppError(404, "not_found", f"Loan {loan_id} does not exist")
    if loan.returned_at is not None:
        raise AppError(409, "conflict", f"Loan {loan_id} has already been returned")

    loan.returned_at = today()
    db.commit()
    db.refresh(loan)
    return loan
