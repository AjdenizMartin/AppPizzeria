from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_manager_or_owner
from app.schemas.report import SalesReportResponse
from app.services.report_service import get_daily_sales_report

router = APIRouter(tags=["reports"])


@router.get("/admin/reports/sales", response_model=SalesReportResponse)
def get_sales_report(
    date_value: date = Query(alias="date"),
    db: Session = Depends(get_db),
    _current_admin=Depends(require_manager_or_owner),
):
    return get_daily_sales_report(db, target_date=date_value)
