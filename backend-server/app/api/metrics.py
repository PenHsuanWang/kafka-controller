from fastapi import APIRouter, Request, Response
from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST
from app.services.store import Store

router = APIRouter()

@router.get("/metrics")
def metrics(request: Request):
    store: Store = getattr(request.app.state, "monitor_store", None)
    if not store:
        return Response(content=b"", media_type=CONTENT_TYPE_LATEST)

    reg = CollectorRegistry()
    g_total = Gauge("kafka_group_total_lag", "Total lag per (group,topic)", ["group","topic"], registry=reg)
    g_p95   = Gauge("kafka_group_time_lag_p95_seconds", "Time lag p95 per (group,topic)", ["group","topic"], registry=reg)

    for (group, topic), dq in store.items():
        if not dq:
            continue
        _, snap = dq[-1]
        g_total.labels(group=group, topic=topic).set(snap.summary.totalLag)
        if snap.summary.timeLagP95Sec is not None:
            g_p95.labels(group=group, topic=topic).set(snap.summary.timeLagP95Sec)

    return Response(generate_latest(reg), media_type=CONTENT_TYPE_LATEST)
