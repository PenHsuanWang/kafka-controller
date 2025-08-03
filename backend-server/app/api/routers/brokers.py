"""Broker snapshot endpoints – list brokers and optional detail view."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import require_jwt
from app.domain.models.cluster import Broker
from app.domain.services.cluster_service import ClusterService
from app.infra.kafka.admin import KafkaAdminFacade

router = APIRouter()


def _get_service(cid: str) -> ClusterService:
    """Instantiate ClusterService for *cid*."""
    return ClusterService(KafkaAdminFacade(bootstrap_servers=cid))


@router.get("/", response_model=list[Broker])
async def list_brokers(
    cid: str = Path(...),
    svc: ClusterService = Depends(_get_service),
    _claims: dict = Depends(require_jwt),
) -> list[Broker]:
    """Return the current broker & JMX snapshot for *cid*."""
    return svc.list_brokers()


@router.get("/{bid}", response_model=Broker)
async def get_broker(
    *,
    cid: str = Path(...),
    bid: int = Path(..., description="Broker ID"),
    svc: ClusterService = Depends(_get_service),
    _claims: dict = Depends(require_jwt),
) -> Broker:
    """Return metrics for broker *bid*."""
    try:
        return svc.get_broker(bid)
    except KeyError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Broker {bid} not found"
        ) from exc