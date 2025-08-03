"""Aggregate all REST sub-routers into `api_router` for fast import."""

from fastapi import APIRouter

from .brokers import router as brokers_router
from .clusters import router as clusters_router
from .consumer_groups import router as consumer_groups_router
from .topics import router as topics_router

api_router = APIRouter()
api_router.include_router(clusters_router, prefix="/clusters", tags=["clusters"])
api_router.include_router(
    brokers_router, prefix="/clusters/{cid}/brokers", tags=["brokers"]
)
api_router.include_router(
    topics_router, prefix="/clusters/{cid}/topics", tags=["topics"]
)
api_router.include_router(
    consumer_groups_router,
    prefix="/clusters/{cid}/consumer-groups",
    tags=["consumer-groups"],
)