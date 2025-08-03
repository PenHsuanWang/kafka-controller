"""Consumer-group listing and offset-reset operations."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, Body, Depends, HTTPException, Path, status

from app.api.dependencies import require_jwt
from app.domain.models.consumer_group import ConsumerGroup, OffsetResetRequest
from app.domain.services.consumer_service import ConsumerService
from app.infra.kafka.admin import KafkaAdminFacade

router = APIRouter()

def _get_service(cid: str = Path(..., description="Cluster ID")) -> ConsumerService:
    """Return a ConsumerService for the provided cluster id (bootstrap server)."""
    return ConsumerService(KafkaAdminFacade(bootstrap_servers=cid))

@router.get("/", response_model=list[ConsumerGroup])
async def list_consumer_groups(
    cid: str = Path(..., description="Cluster ID"),  # FastAPI injects this from the mounting prefix
    svc: ConsumerService = Depends(_get_service),
    _: dict = Depends(require_jwt),  # unused claims → “_”
) -> list[ConsumerGroup]:
    """Return consumer groups with aggregate lag."""
    return svc.list_groups()

@router.post("/{gid}/offsets:reset", status_code=status.HTTP_200_OK)
async def reset_offsets(
    cid: str = Path(..., description="Cluster ID"),
    gid: str = Path(..., description="Consumer-group ID"),
    payload: OffsetResetRequest = Body(...),
    svc: ConsumerService = Depends(_get_service),
    _: dict = Depends(require_jwt),
) -> dict[str, bool]:
    """Reset offsets for *gid* according to *payload*."""
    try:
        svc.reset_offsets(gid, payload)
        return {"ack": True}
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc