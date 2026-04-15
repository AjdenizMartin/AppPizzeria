from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_print_agent
from app.schemas.order import PrintJobRead
from app.schemas.printing import (
    PrintAgentJobFailRequest,
    PrintAgentJobResolveRequest,
    PrintAgentPullRequest,
    PrintAgentPullResponse,
)
from app.services.printing_service import (
    mark_print_job_completed,
    mark_print_job_failed,
    pull_next_print_job,
)

router = APIRouter(prefix="/print-agent", tags=["print-agent"])


def _build_job_payload(job) -> dict:
    return {
        "job_id": job.id,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "order": {
            "id": job.order.id,
            "status": job.order.status,
            "total_price": job.order.total_price,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price": item.price,
                    "extras": item.extras or "",
                }
                for item in job.order.items
            ],
        },
    }


@router.post("/jobs/pull", response_model=PrintAgentPullResponse)
def pull_print_job(
    payload: PrintAgentPullRequest,
    db: Session = Depends(get_db),
    _agent_auth=Depends(require_print_agent),
):
    job = pull_next_print_job(db, agent_id=payload.agent_id.strip())
    if job is None:
        return {"job": None}
    return {"job": _build_job_payload(job)}


@router.post("/jobs/{job_id}/complete", response_model=PrintJobRead)
def complete_print_job(
    job_id: int,
    payload: PrintAgentJobResolveRequest,
    db: Session = Depends(get_db),
    _agent_auth=Depends(require_print_agent),
):
    try:
        return mark_print_job_completed(db, job_id=job_id, agent_id=payload.agent_id.strip())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/fail", response_model=PrintJobRead)
def fail_print_job(
    job_id: int,
    payload: PrintAgentJobFailRequest,
    db: Session = Depends(get_db),
    _agent_auth=Depends(require_print_agent),
):
    try:
        return mark_print_job_failed(
            db,
            job_id=job_id,
            agent_id=payload.agent_id.strip(),
            error=payload.error,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
