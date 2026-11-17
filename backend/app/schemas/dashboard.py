from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DashboardSummaryResponse(BaseModel):
    total_machines_tested: int
    total_production_records: int
    approved_records: int
    pending_records: int
    rejected_records: int
    average_cycle_time_hours: float
    total_testing_time_hours: float
    total_ncs: int
    open_ncs: int
    closed_ncs: int
    nc_rate_percentage: float
    total_rework_minutes: float


class TrendItem(BaseModel):
    label: str
    count: int
    secondary_value: Optional[float] = 0.0


class CategoryDistributionItem(BaseModel):
    category: str
    count: int
    percentage: float


class ProductionDashboardResponse(BaseModel):
    total_production: int
    total_machines_tested: int
    average_cycle_time_hours: float
    total_testing_minutes: float
    daily_trends: List[TrendItem]
    monthly_trends: List[TrendItem]
    machine_wise_production: List[TrendItem]
    shift_wise_production: List[TrendItem]
    customer_wise_production: List[TrendItem]


class QualityDashboardResponse(BaseModel):
    total_ncs: int
    open_ncs: int
    in_progress_ncs: int
    under_review_ncs: int
    closed_ncs: int
    nc_rate_percentage: float
    total_rework_minutes: float
    category_distribution: List[CategoryDistributionItem]
    severity_distribution: List[CategoryDistributionItem]
    monthly_nc_trends: List[TrendItem]
    department_distribution: List[CategoryDistributionItem]


class MachinePerformanceItem(BaseModel):
    machine_id: int
    machine_code: str
    machine_name: str
    total_tests: int
    pass_tests: int
    fail_tests: int
    pass_rate_percentage: float
    average_cycle_time_hours: float
    total_testing_time_minutes: float
    total_ncs: int
    total_rework_minutes: float


class MachineDashboardResponse(BaseModel):
    machines: List[MachinePerformanceItem]

