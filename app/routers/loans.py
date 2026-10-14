"""Loan creation endpoint.

The shared contract is declared here; the loan ticket fills the handler body
with the lending rules. It currently answers 501 in the uniform error envelope.
"""

from fastapi import APIRouter, Depends

from ..errors import AppError, documented_errors
from ..schemas import LoanCreate, LoanRead
from ..security import require_api_key

router = APIRouter(tags=["loans"])


@router.post(
    "/loans",
    response_model=LoanRead,
    status_code=201,
    responses=documented_errors(401, 404, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def create_loan(payload: LoanCreate) -> LoanRead:
    raise AppError(501, "not_implemented", "POST /loans is not implemented yet")
