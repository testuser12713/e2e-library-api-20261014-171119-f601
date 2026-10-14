"""Loan return endpoint.

The shared contract is declared here; the loan-return ticket fills the handler
body. It currently answers 501 in the uniform error envelope.
"""

from fastapi import APIRouter, Depends

from ..errors import AppError, documented_errors
from ..schemas import LoanRead
from ..security import require_api_key

router = APIRouter(tags=["loans"])


@router.post(
    "/loans/{loan_id}/return",
    response_model=LoanRead,
    responses=documented_errors(401, 404, 409),
    dependencies=[Depends(require_api_key)],
)
def return_loan(loan_id: int) -> LoanRead:
    raise AppError(501, "not_implemented", "POST /loans/{loan_id}/return is not implemented yet")
