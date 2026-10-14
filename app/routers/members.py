"""Member endpoints: CRUD with pagination and a loan-aware delete guard."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import AppError, documented_errors
from ..models import Loan, Member
from ..schemas import MemberPage, MemberPatch, MemberRead, MemberWrite
from ..security import require_api_key

router = APIRouter(tags=["members"])


def _get_member_or_404(db: Session, member_id: int) -> Member:
    """Return the member with ``member_id`` or raise a 404 envelope error."""
    member = db.get(Member, member_id)
    if member is None:
        raise AppError(404, "not_found", f"Member {member_id} not found")
    return member


def _email_taken(db: Session, email: str, *, exclude_id: int | None = None) -> bool:
    """Report whether another member already uses ``email``."""
    statement = select(Member.id).where(Member.email == email)
    if exclude_id is not None:
        statement = statement.where(Member.id != exclude_id)
    return db.execute(statement).first() is not None


@router.post(
    "/members",
    response_model=MemberRead,
    status_code=201,
    responses=documented_errors(401, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def create_member(payload: MemberWrite, db: Session = Depends(get_db)) -> MemberRead:
    if _email_taken(db, payload.email):
        raise AppError(409, "conflict", f"Email '{payload.email}' is already in use")
    member = Member(name=payload.name, email=payload.email)
    db.add(member)
    db.commit()
    db.refresh(member)
    return MemberRead.model_validate(member)


@router.get("/members", response_model=MemberPage, responses=documented_errors(422))
def list_members(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> MemberPage:
    total = db.execute(select(func.count()).select_from(Member)).scalar_one()
    members = (
        db.execute(select(Member).order_by(Member.id).limit(limit).offset(offset)).scalars().all()
    )
    return MemberPage(
        items=[MemberRead.model_validate(member) for member in members],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/members/{member_id}", response_model=MemberRead, responses=documented_errors(404))
def get_member(member_id: int, db: Session = Depends(get_db)) -> MemberRead:
    return MemberRead.model_validate(_get_member_or_404(db, member_id))


@router.put(
    "/members/{member_id}",
    response_model=MemberRead,
    responses=documented_errors(401, 404, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def replace_member(
    member_id: int, payload: MemberWrite, db: Session = Depends(get_db)
) -> MemberRead:
    member = _get_member_or_404(db, member_id)
    if _email_taken(db, payload.email, exclude_id=member_id):
        raise AppError(409, "conflict", f"Email '{payload.email}' is already in use")
    member.name = payload.name
    member.email = payload.email
    db.commit()
    db.refresh(member)
    return MemberRead.model_validate(member)


@router.patch(
    "/members/{member_id}",
    response_model=MemberRead,
    responses=documented_errors(401, 404, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def update_member(
    member_id: int, payload: MemberPatch, db: Session = Depends(get_db)
) -> MemberRead:
    member = _get_member_or_404(db, member_id)
    changes = payload.model_dump(exclude_unset=True)
    new_email = changes.get("email")
    if new_email is not None and _email_taken(db, new_email, exclude_id=member_id):
        raise AppError(409, "conflict", f"Email '{new_email}' is already in use")
    for field, value in changes.items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return MemberRead.model_validate(member)


@router.delete(
    "/members/{member_id}",
    status_code=204,
    responses=documented_errors(401, 404, 409),
    dependencies=[Depends(require_api_key)],
)
def delete_member(member_id: int, db: Session = Depends(get_db)) -> None:
    member = _get_member_or_404(db, member_id)
    loan_count = db.execute(
        select(func.count()).select_from(Loan).where(Loan.member_id == member_id)
    ).scalar_one()
    if loan_count > 0:
        raise AppError(
            409,
            "conflict",
            f"Member {member_id} still has {loan_count} loan(s)",
        )
    db.delete(member)
    db.commit()
