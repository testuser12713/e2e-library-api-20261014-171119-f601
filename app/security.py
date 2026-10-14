"""API-key dependency attached to every write endpoint.

``require_api_key`` compares the ``X-API-Key`` header against the configured
``Settings.library_api_key``. A missing header, an unconfigured key or a
mismatching value all raise :class:`AppError` with status 401, which the
handlers in :mod:`app.errors` render in the uniform error envelope.
"""

import hmac
from typing import Annotated

from fastapi import Header

from .config import get_settings
from .errors import AppError


def require_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Reject the request unless it carries the configured API key."""
    configured_key = get_settings().library_api_key
    if configured_key is None or not x_api_key:
        raise AppError(401, "unauthorized", "A valid X-API-Key header is required")
    if not hmac.compare_digest(x_api_key, configured_key):
        raise AppError(401, "unauthorized", "A valid X-API-Key header is required")
