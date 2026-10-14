"""Overdue loans endpoint.

The shared contract is declared here; the overdue ticket fills the handler body.
It currently answers 501 in the uniform error envelope.
"""

from fastapi import APIRouter, Query

from ..errors import AppError, documented_errors
from ..schemas import OverduePage

router = APIRouter(tags=["loans"])


@router.get("/loans/overdue", response_model=OverduePage, responses=documented_errors(422))
def list_overdue_loans(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> OverduePage:
    raise AppError(501, "not_implemented", "GET /loans/overdue is not implemented yet")
