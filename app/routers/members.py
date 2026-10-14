"""Member endpoints.

The shared contract is declared here; the member CRUD ticket fills the handler
bodies. Every handler currently answers 501 in the uniform error envelope.
"""

from fastapi import APIRouter, Depends, Query

from ..errors import AppError, documented_errors
from ..schemas import MemberPage, MemberPatch, MemberRead, MemberWrite
from ..security import require_api_key

router = APIRouter(tags=["members"])


@router.post(
    "/members",
    response_model=MemberRead,
    status_code=201,
    responses=documented_errors(401, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def create_member(payload: MemberWrite) -> MemberRead:
    raise AppError(501, "not_implemented", "POST /members is not implemented yet")


@router.get("/members", response_model=MemberPage, responses=documented_errors(422))
def list_members(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> MemberPage:
    raise AppError(501, "not_implemented", "GET /members is not implemented yet")


@router.get("/members/{member_id}", response_model=MemberRead, responses=documented_errors(404))
def get_member(member_id: int) -> MemberRead:
    raise AppError(501, "not_implemented", "GET /members/{member_id} is not implemented yet")


@router.put(
    "/members/{member_id}",
    response_model=MemberRead,
    responses=documented_errors(401, 404, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def replace_member(member_id: int, payload: MemberWrite) -> MemberRead:
    raise AppError(501, "not_implemented", "PUT /members/{member_id} is not implemented yet")


@router.patch(
    "/members/{member_id}",
    response_model=MemberRead,
    responses=documented_errors(401, 404, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def update_member(member_id: int, payload: MemberPatch) -> MemberRead:
    raise AppError(501, "not_implemented", "PATCH /members/{member_id} is not implemented yet")


@router.delete(
    "/members/{member_id}",
    status_code=204,
    responses=documented_errors(401, 404, 409),
    dependencies=[Depends(require_api_key)],
)
def delete_member(member_id: int) -> None:
    raise AppError(501, "not_implemented", "DELETE /members/{member_id} is not implemented yet")
