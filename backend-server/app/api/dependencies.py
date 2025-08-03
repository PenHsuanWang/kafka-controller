"""Global reusable FastAPI dependencies (DB, JWT, pagination, etc.)."""
from fastapi import Depends, Header, HTTPException, status

from app.core.security import decode_jwt


async def require_jwt(
    authorization: str | None = Header(default=None, alias="Authorization")
) -> dict:
    """Validate a Bearer JWT and return the decoded claims."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.removeprefix("Bearer ").strip()
    return decode_jwt(token)