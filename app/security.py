"""API-key dependency attached to every write endpoint.

The check itself is deliberately inert in this skeleton: the signature is the
shared contract, and the API-key ticket fills the body with the actual
comparison against ``Settings.library_api_key``.
"""

from typing import Annotated

from fastapi import Header


def require_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Placeholder dependency; the API-key ticket implements the real check."""
    return None
