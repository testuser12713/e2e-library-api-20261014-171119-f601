"""The uniform error envelope and the exception handlers that render it.

Every failure response - including 401, 404, 409, 422 and an unfilled stub's
501 - has the shape ``{"error": {"code": <str>, "message": <str>}}``.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .schemas import ErrorResponse

logger = logging.getLogger(__name__)

_CODE_BY_STATUS: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    500: "internal_error",
    501: "not_implemented",
}

ERROR_RESPONSES: dict[int, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "Conflict with existing data"},
    422: {"model": ErrorResponse, "description": "Input validation failed"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
    501: {"model": ErrorResponse, "description": "Not implemented yet"},
}


class AppError(Exception):
    """Domain error raised by the routers; rendered through the error envelope."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Build a JSON error response in the uniform envelope."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def documented_errors(*statuses: int) -> dict[int, dict[str, Any]]:
    """Return OpenAPI ``responses`` entries for the given error statuses."""
    return {status: ERROR_RESPONSES[status] for status in statuses if status in ERROR_RESPONSES}


def _code_for_status(status_code: int) -> str:
    return _CODE_BY_STATUS.get(status_code, "http_error")


def _field_from_loc(loc: tuple[Any, ...]) -> str:
    parts = [str(part) for part in loc if part not in ("body", "query", "path", "header", "cookie")]
    return ".".join(parts) if parts else "body"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Render an :class:`AppError` through the uniform envelope."""
    return error_response(exc.status_code, exc.code, exc.message)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Render any framework ``HTTPException`` (e.g. an unknown path's 404)."""
    return error_response(exc.status_code, _code_for_status(exc.status_code), str(exc.detail))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Render a 422 envelope whose message names the offending field."""
    errors = exc.errors()
    if errors:
        first = errors[0]
        field = _field_from_loc(tuple(first.get("loc", ())))
        message = f"Invalid value for field '{field}': {first.get('msg', 'invalid value')}"
    else:
        message = "Request validation failed"
    return error_response(422, "validation_error", message)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render an unexpected error as a 500 envelope and log it for debugging."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "internal_error", "Internal Server Error")


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every envelope-rendering handler to the application."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
