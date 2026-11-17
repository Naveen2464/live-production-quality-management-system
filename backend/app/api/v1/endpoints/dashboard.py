from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    ProductionDashboardResponse,
    QualityDashboardResponse,
    MachineDashboardResponse
)
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse, summary="Get executive top-level summary metrics")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Provides overall operational figures: total machines tested, production records, cycle time, NC counts, and rework."""
    return DashboardService.get_summary_metrics(db=db)


@router.get("/production", response_model=ProductionDashboardResponse, summary="Get production analytics and charts")
def get_production_dashboard(
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    machine_id: Optional[int] = Query(None, description="Filter by Machine ID"),
    shift_id: Optional[int] = Query(None, description="Filter by Shift ID"),
    customer_id: Optional[int] = Query(None, description="Filter by Customer ID"),
    db: Session = Depends(get_db)
):
    """Provides daily/monthly trends, machine-wise and shift-wise breakdown from live database records."""
    return DashboardService.get_production_analytics(
        db=db,
        start_date=start_date,
        end_date=end_date,
        machine_id=machine_id,
        shift_id=shift_id,
        customer_id=customer_id
    )


@router.get("/quality", response_model=QualityDashboardResponse, summary="Get quality and NC analytics")
def get_quality_dashboard(
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    machine_id: Optional[int] = Query(None, description="Filter by Machine ID"),
    db: Session = Depends(get_db)
):
    """Provides NC defect category distribution, severity breakdown, monthly trends, and rework minutes."""
    return DashboardService.get_quality_analytics(
        db=db,
        start_date=start_date,
        end_date=end_date,
        machine_id=machine_id
    )


@router.get("/machines", response_model=MachineDashboardResponse, summary="Get machine performance comparison")
def get_machine_performance_dashboard(db: Session = Depends(get_db)):
    """Provides machine-by-machine production volume, pass rates, cycle times, quality issues and rework."""
    return DashboardService.get_machine_performance(db=db)

