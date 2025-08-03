"""Helpers for encoding and decoding JSON Web Tokens (JWT).

The implementation is intentionally minimal:
* HS256 symmetric signing (default) – easy to rotate via env vars.
* 30-minute default lifetime, overridable per-call.
* Pure business logic – no FastAPI imports, so it is unit-testable in isolation.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

from jose import JWTError, jwt  # python-jose
from pydantic import ValidationError

from app.core.config import get_settings

settings = get_settings()


class TokenValidationError(Exception):
    """Raised when a JWT is missing or invalid."""


def create_access_token(
    claims: Dict[str, Any],
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Return a signed JWT embedding *claims*."""
    to_encode = claims.copy()
    expire = datetime.utcnow() + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

def decode_jwt(token: str) -> Dict[str, Any]:
    """Validate *token* and return its claims dict.

    Raises
    ------
    TokenValidationError
        If the token is malformed, expired, or signature-invalid.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except (JWTError, ValidationError) as exc:
        raise TokenValidationError("Invalid or expired JWT") from exc