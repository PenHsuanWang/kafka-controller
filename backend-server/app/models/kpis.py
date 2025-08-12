from pydantic import BaseModel


class Throughput(BaseModel):
    bytesInPerSec: float
    bytesOutPerSec: float
    messagesInPerSec: float


class ClusterKPIs(BaseModel):
    brokersOnline: int
    underReplicatedPartitions: int
    activeControllerCount: int
    controllerElections24h: int | None = None
    throughput: Throughput
