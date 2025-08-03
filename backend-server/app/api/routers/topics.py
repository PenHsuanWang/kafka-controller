"""Topic CRUD endpoints (idempotent create / two-phase delete)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.dependencies import require_jwt
from app.domain.models.topic import Topic
from app.domain.services.topic_service import TopicService
from app.infra.kafka.admin import KafkaAdminFacade

router = APIRouter()


# ---------- dependency helpers -------------------------------------------------
def _get_service(cid: str) -> TopicService:
    """Instantiate TopicService for *cid* cluster."""
    return TopicService(KafkaAdminFacade(bootstrap_servers=cid))


# ---------- routes -------------------------------------------------------------
@router.get("/", response_model=list[Topic])
async def list_topics(
    *,
    cid: str = Path(...),
    q: str | None = Query(default=None, description="Name filter (contains)"),
    svc: TopicService = Depends(_get_service),
    _claims: dict = Depends(require_jwt),
) -> list[Topic]:
    """Return (optionally filtered) topics for *cid*."""
    return svc.list_topics(name_filter=q)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_topic(
    *,
    cid: str = Path(...),
    topic: Topic,
    svc: TopicService = Depends(_get_service),
    _claims: dict = Depends(require_jwt),
) -> None:
    """Create *topic* idempotently."""
    svc.create_topic(topic)


@router.delete("/{topic_name}", status_code=status.HTTP_202_ACCEPTED)
async def schedule_delete_topic(
    *,
    cid: str = Path(...),
    topic_name: str = Path(..., regex=r"^[\w.\-]+$"),
    confirm: str | None = Query(
        default=None,
        description="Confirmation UUID returned by `POST /actions/prepare` (spec §3)",
    ),
    svc: TopicService = Depends(_get_service),
    _claims: dict = Depends(require_jwt),
) -> None:
    """Schedule deletion of *topic_name* (two-phase)."""
    try:
        svc.schedule_delete_topic(topic_name, confirm)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc