from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_admin
from app.core.observability import metrics

router = APIRouter(prefix="/admin/metrics", tags=["ops"])


@router.post("/reset")
def reset_metrics(_current_admin=Depends(get_current_admin)):
    metrics.reset()
    return {"ok": True, "message": "Metrics reset"}


@router.get("/events")
def list_operational_events(
    event: str | None = Query(default=None, min_length=2, max_length=120),
    limit: int = Query(default=20, ge=1, le=200),
    _current_admin=Depends(get_current_admin),
):
    snapshot = metrics.snapshot()
    events = snapshot.recent_critical_events

    if event:
        events = [entry for entry in events if entry["event"] == event]

    return {
        "events": events[:limit],
        "count": len(events[:limit]),
    }
