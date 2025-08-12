from __future__ import annotations
from fastapi import APIRouter
from app.models.kpis import ClusterKPIs, Throughput
from app.services.kafka_service import KafkaService
from app.services.jmx_service import JmxService

router = APIRouter(tags=["cluster"])

@router.get("/cluster", response_model=ClusterKPIs)
def get_cluster():
    kafka = KafkaService()
    jmx = JmxService()
    j = jmx.cluster_kpis()
    data = {
        "brokersOnline": kafka.brokers_online(),
        "underReplicatedPartitions": j["underReplicatedPartitions"],
        "activeControllerCount": j["activeControllerCount"],
        "controllerElections24h": None,
        "throughput": j["throughput"],
    }
    return ClusterKPIs(
        brokersOnline=data["brokersOnline"],
        underReplicatedPartitions=data["underReplicatedPartitions"],
        activeControllerCount=data["activeControllerCount"],
        controllerElections24h=data["controllerElections24h"],
        throughput=Throughput(**data["throughput"]),
    )