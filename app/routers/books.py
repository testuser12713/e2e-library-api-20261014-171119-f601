"""Book endpoints.

The shared contract is declared here; the book CRUD ticket fills the handler
bodies. Every handler currently answers 501 in the uniform error envelope.
"""

from fastapi import APIRouter, Depends, Query

from ..errors import AppError, documented_errors
from ..schemas import BookPage, BookPatch, BookRead, BookWrite
from ..security import require_api_key

router = APIRouter(tags=["books"])


@router.post(
    "/books",
    response_model=BookRead,
    status_code=201,
    responses=documented_errors(401, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def create_book(payload: BookWrite) -> BookRead:
    raise AppError(501, "not_implemented", "POST /books is not implemented yet")


@router.get("/books", response_model=BookPage, responses=documented_errors(422))
def list_books(
    q: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> BookPage:
    raise AppError(501, "not_implemented", "GET /books is not implemented yet")


@router.get("/books/{book_id}", response_model=BookRead, responses=documented_errors(404))
def get_book(book_id: int) -> BookRead:
    raise AppError(501, "not_implemented", "GET /books/{book_id} is not implemented yet")


@router.put(
    "/books/{book_id}",
    response_model=BookRead,
    responses=documented_errors(401, 404, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def replace_book(book_id: int, payload: BookWrite) -> BookRead:
    raise AppError(501, "not_implemented", "PUT /books/{book_id} is not implemented yet")


@router.patch(
    "/books/{book_id}",
    response_model=BookRead,
    responses=documented_errors(401, 404, 409, 422),
    dependencies=[Depends(require_api_key)],
)
def update_book(book_id: int, payload: BookPatch) -> BookRead:
    raise AppError(501, "not_implemented", "PATCH /books/{book_id} is not implemented yet")


@router.delete(
    "/books/{book_id}",
    status_code=204,
    responses=documented_errors(401, 404, 409),
    dependencies=[Depends(require_api_key)],
)
def delete_book(book_id: int) -> None:
    raise AppError(501, "not_implemented", "DELETE /books/{book_id} is not implemented yet")
