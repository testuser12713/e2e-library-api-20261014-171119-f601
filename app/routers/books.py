"""Book endpoints: CRUD with search and pagination.

Every failure is raised as an :class:`AppError` and rendered through the uniform
error envelope. Uniqueness of ``isbn`` is enforced both by an explicit check for
a friendly 409 and by the database constraint as a backstop.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..errors import AppError, documented_errors
from ..models import Book, Loan
from ..schemas import BookPage, BookPatch, BookRead, BookWrite
from ..security import require_api_key

router = APIRouter(tags=["books"])


def _load_book(db: Session, book_id: int) -> Book:
    """Return the book or raise a 404 ``AppError``."""
    book = db.get(Book, book_id)
    if book is None:
        raise AppError(404, "not_found", f"Book {book_id} not found")
    return book


def _loan_count(db: Session, book_id: int, *, open_only: bool = False) -> int:
    """Count the loans referencing a book, optionally only the open ones."""
    stmt = select(func.count()).select_from(Loan).where(Loan.book_id == book_id)
    if open_only:
        stmt = stmt.where(Loan.returned_at.is_(None))
    return db.scalar(stmt) or 0


def _isbn_taken(db: Session, isbn: str, *, exclude_id: int | None = None) -> bool:
    """Return whether another book already uses this ISBN."""
    stmt = select(Book.id).where(Book.isbn == isbn)
    if exclude_id is not None:
        stmt = stmt.where(Book.id != exclude_id)
    return db.scalar(stmt) is not None


def _commit(db: Session, isbn: str) -> None:
    """Commit, translating a database uniqueness violation into a 409."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "conflict", f"ISBN '{isbn}' is already used by another book") from None


@router.post(
    "/books",
    response_model=BookRead,
    status_code=201,
    responses=documented_errors(401, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def create_book(payload: BookWrite, db: Session = Depends(get_db)) -> Book:
    """Create a book; an already used ISBN is refused with 409."""
    if _isbn_taken(db, payload.isbn):
        raise AppError(409, "conflict", f"ISBN '{payload.isbn}' is already used by another book")

    book = Book(**payload.model_dump())
    db.add(book)
    _commit(db, payload.isbn)
    db.refresh(book)
    return book


@router.get("/books", response_model=BookPage, responses=documented_errors(422))
def list_books(
    q: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> BookPage:
    """Return a page of books, optionally filtered by a title/author substring."""
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(or_(Book.title.ilike(pattern), Book.author.ilike(pattern)))

    total = db.scalar(select(func.count()).select_from(Book).where(*filters)) or 0

    stmt = select(Book).order_by(Book.id).limit(limit).offset(offset)
    if filters:
        stmt = stmt.where(*filters)
    books = db.scalars(stmt).all()

    return BookPage(
        items=[BookRead.model_validate(book) for book in books],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/books/{book_id}", response_model=BookRead, responses=documented_errors(404))
def get_book(book_id: int, db: Session = Depends(get_db)) -> Book:
    """Return a single book or 404."""
    return _load_book(db, book_id)


@router.put(
    "/books/{book_id}",
    response_model=BookRead,
    responses=documented_errors(401, 404, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def replace_book(book_id: int, payload: BookWrite, db: Session = Depends(get_db)) -> Book:
    """Fully replace a book; refuse a duplicate ISBN or too few copies."""
    book = _load_book(db, book_id)
    if _isbn_taken(db, payload.isbn, exclude_id=book_id):
        raise AppError(409, "conflict", f"ISBN '{payload.isbn}' is already used by another book")

    open_loans = _loan_count(db, book_id, open_only=True)
    if payload.copies < open_loans:
        raise AppError(
            409,
            "conflict",
            f"Cannot set copies below the {open_loans} open loan(s) of book {book_id}",
        )

    book.title = payload.title
    book.author = payload.author
    book.isbn = payload.isbn
    book.published_year = payload.published_year
    book.copies = payload.copies
    _commit(db, payload.isbn)
    db.refresh(book)
    return book


@router.patch(
    "/books/{book_id}",
    response_model=BookRead,
    responses=documented_errors(401, 404, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def update_book(book_id: int, payload: BookPatch, db: Session = Depends(get_db)) -> Book:
    """Partially update a book; refuse a duplicate ISBN or too few copies."""
    book = _load_book(db, book_id)
    changes = payload.model_dump(exclude_unset=True)

    if "isbn" in changes and _isbn_taken(db, changes["isbn"], exclude_id=book_id):
        raise AppError(409, "conflict", f"ISBN '{changes['isbn']}' is already used by another book")

    if "copies" in changes:
        open_loans = _loan_count(db, book_id, open_only=True)
        if changes["copies"] < open_loans:
            raise AppError(
                409,
                "conflict",
                f"Cannot set copies below the {open_loans} open loan(s) of book {book_id}",
            )

    for field, value in changes.items():
        setattr(book, field, value)
    _commit(db, book.isbn)
    db.refresh(book)
    return book


@router.delete(
    "/books/{book_id}",
    status_code=204,
    responses=documented_errors(401, 404, 409),
    dependencies=[Depends(require_api_key)],
)
def delete_book(book_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a book; refuse while loans still reference it, naming their count."""
    book = _load_book(db, book_id)

    loans = _loan_count(db, book_id)
    if loans:
        raise AppError(
            409,
            "conflict",
            f"Cannot delete book {book_id}: {loans} loan(s) still reference it",
        )

    db.delete(book)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            409, "conflict", f"Cannot delete book {book_id}: loans still reference it"
        ) from None
