"""Cluster-level endpoints: list clusters, show cluster summary."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import require_jwt
from app.domain.models.cluster import Cluster
from app.domain.services.cluster_service import ClusterService
from app.infra.kafka.admin import KafkaAdminFacade

router = APIRouter()


# ---------- dependency helpers -------------------------------------------------
def _get_service() -> ClusterService:
    """Simple factory – swap with a DI container if desired."""
    return ClusterService(KafkaAdminFacade(bootstrap_servers="localhost:9092"))


# ---------- routes -------------------------------------------------------------
@router.get("/", response_model=list[Cluster])
async def list_clusters(
    svc: ClusterService = Depends(_get_service),
    _claims: dict = Depends(require_jwt),
) -> list[Cluster]:
    """Return all configured Kafka clusters."""
    return svc.list_clusters()


@router.get("/{cid}", response_model=Cluster)
async def get_cluster(
    cid: str = Path(..., description="Cluster identifier"),
    svc: ClusterService = Depends(_get_service),
    _claims: dict = Depends(require_jwt),
) -> Cluster:
    """Return summary health information for *cid*."""
    try:
        return svc.get_cluster(cid)
    except KeyError as exc:  # raised by the service layer
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Cluster '{cid}' not found"
        ) from exc