"""RFC 7807 *Problem Details* support for FastAPI."""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings

settings = get_settings()


class ProblemDetail(BaseModel):
    """Data model that serialises to RFC 7807 JSON.

    Attributes
    ----------
    type : str
        A URI reference that identifies the problem type.
    title : str
        A short human-readable summary of the problem type.
    status : int
        The HTTP status code.
    detail : str | None
        A human-readable explanation specific to this occurrence.
    instance : str
        A URI reference that identifies the specific occurrence.
    """

    type: str = Field(..., examples=["/validation-error"])
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: Optional[str] = None
    instance: str = Field(default_factory=lambda: f"urn:uuid:{uuid4()}")

    class Config:
        json_schema_extra = {"required": ["type", "title", "status"]}


class ProblemDetailException(Exception):
    """Raise inside services/routers to trigger a 7807 response."""

    def __init__(
        self,
        status_code: int,
        title: str,
        type_: str = "about:blank",
        detail: Optional[str] = None,
    ) -> None:
        self.problem = ProblemDetail(
            status=status_code,
            title=title,
            type=type_,
            detail=detail,
        )


# --------------------------------------------------------------------------- #
# FastAPI integration                                                         #
# --------------------------------------------------------------------------- #
def add_problem_detail_handler(app: FastAPI) -> None:
    """Register a global exception handler for ProblemDetailException."""

    @app.exception_handler(ProblemDetailException)
    async def _handler(
        request: Request, exc: ProblemDetailException  # noqa: W0613
    ) -> JSONResponse:
        return JSONResponse(
            content=exc.problem.model_dump(mode="json"),
            status_code=exc.problem.status,
            media_type="application/problem+json",
        )

    # You can also optionally convert FastAPI's HTTPException or
    # pydantic errors here to ProblemDetail for uniformity.
