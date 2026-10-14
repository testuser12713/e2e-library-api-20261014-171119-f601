"""Pydantic v2 request and response schemas for the library API."""

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .clock import today

MIN_PUBLISHED_YEAR = 1000


def _max_published_year() -> int:
    return today().year + 1


class ErrorDetail(BaseModel):
    """Machine-readable error payload."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """The uniform error envelope used by every failure response."""

    error: ErrorDetail


class BookWrite(BaseModel):
    """Payload for creating or fully replacing a book."""

    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    isbn: str = Field(min_length=1)
    published_year: int
    copies: int = Field(ge=0)

    @field_validator("published_year")
    @classmethod
    def _validate_published_year(cls, value: int) -> int:
        max_year = _max_published_year()
        if not MIN_PUBLISHED_YEAR <= value <= max_year:
            raise ValueError(f"must be between {MIN_PUBLISHED_YEAR} and {max_year}")
        return value


class BookPatch(BaseModel):
    """Payload for partially updating a book; every field is optional."""

    title: str | None = Field(default=None, min_length=1)
    author: str | None = Field(default=None, min_length=1)
    isbn: str | None = Field(default=None, min_length=1)
    published_year: int | None = None
    copies: int | None = Field(default=None, ge=0)

    @field_validator("published_year")
    @classmethod
    def _validate_published_year(cls, value: int | None) -> int | None:
        if value is None:
            return value
        max_year = _max_published_year()
        if not MIN_PUBLISHED_YEAR <= value <= max_year:
            raise ValueError(f"must be between {MIN_PUBLISHED_YEAR} and {max_year}")
        return value


class BookRead(BaseModel):
    """A book as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    published_year: int
    copies: int


class MemberWrite(BaseModel):
    """Payload for creating or fully replacing a member."""

    name: str = Field(min_length=1)
    email: EmailStr


class MemberPatch(BaseModel):
    """Payload for partially updating a member; every field is optional."""

    name: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = None


class MemberRead(BaseModel):
    """A member as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    member_since: date


class LoanCreate(BaseModel):
    """Payload for creating a loan."""

    book_id: int = Field(gt=0)
    member_id: int = Field(gt=0)


class LoanRead(BaseModel):
    """A loan as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    member_id: int
    loaned_at: date
    due_at: date
    returned_at: date | None


class OverdueLoanRead(BaseModel):
    """An overdue loan with the number of days it is past due."""

    book_id: int
    member_id: int
    loaned_at: date
    due_at: date
    days_overdue: int


class BookPage(BaseModel):
    """A paginated page of books."""

    items: list[BookRead]
    total: int
    limit: int
    offset: int


class MemberPage(BaseModel):
    """A paginated page of members."""

    items: list[MemberRead]
    total: int
    limit: int
    offset: int


class OverduePage(BaseModel):
    """A paginated page of overdue loans."""

    items: list[OverdueLoanRead]
    total: int
    limit: int
    offset: int
