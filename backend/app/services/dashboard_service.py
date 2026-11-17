from datetime import date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, desc, or_

from app.models.all_models import (
    ProductionRecord, QualityRecord, NCRecord, ReworkRecord,
    Machine, Customer, Shift, Frame, ApprovalStatusEnum, NCStatusEnum
)
from app.schemas.dashboard import (
    DashboardSummaryResponse, ProductionDashboardResponse,
    QualityDashboardResponse, MachineDashboardResponse,
    TrendItem, CategoryDistributionItem, MachinePerformanceItem
)


class DashboardService:

    @classmethod
    def get_summary_metrics(cls, db: Session) -> DashboardSummaryResponse:
        """Retrieves top-level executive KPI metrics directly from PostgreSQL records."""
        total_prod = db.query(func.count(ProductionRecord.id)).scalar() or 0
        distinct_machines = db.query(func.count(distinct(ProductionRecord.machine_id))).scalar() or 0
        
        approved_cnt = db.query(func.count(ProductionRecord.id)).filter(
            ProductionRecord.approval_status == ApprovalStatusEnum.APPROVED.value
        ).scalar() or 0
        pending_cnt = db.query(func.count(ProductionRecord.id)).filter(
            ProductionRecord.approval_status == ApprovalStatusEnum.PENDING.value
        ).scalar() or 0
        rejected_cnt = db.query(func.count(ProductionRecord.id)).filter(
            ProductionRecord.approval_status == ApprovalStatusEnum.REJECTED.value
        ).scalar() or 0

        avg_cycle_hours = db.query(func.avg(ProductionRecord.cycle_time_hours)).scalar() or 0.0
        total_test_mins = db.query(func.sum(ProductionRecord.total_testing_time)).scalar() or 0.0

        total_ncs = db.query(func.count(NCRecord.id)).scalar() or 0
        open_ncs = db.query(func.count(NCRecord.id)).filter(
            NCRecord.status.in_([NCStatusEnum.OPEN.value, NCStatusEnum.IN_PROGRESS.value, NCStatusEnum.UNDER_REVIEW.value])
        ).scalar() or 0
        closed_ncs = db.query(func.count(NCRecord.id)).filter(
            NCRecord.status == NCStatusEnum.CLOSED.value
        ).scalar() or 0

        nc_rate = round((total_ncs / total_prod * 100.0), 2) if total_prod > 0 else 0.0

        # Total rework minutes from rework_records + quality_records
        rework_table_sum = db.query(func.sum(ReworkRecord.rework_minutes)).scalar() or 0.0
        rework_prod_sum = db.query(func.sum(ProductionRecord.rework_time)).scalar() or 0.0
        total_rework = max(float(rework_table_sum), float(rework_prod_sum))

        return DashboardSummaryResponse(
            total_machines_tested=distinct_machines,
            total_production_records=total_prod,
            approved_records=approved_cnt,
            pending_records=pending_cnt,
            rejected_records=rejected_cnt,
            average_cycle_time_hours=round(float(avg_cycle_hours), 2),
            total_testing_time_hours=round(float(total_test_mins) / 60.0, 2),
            total_ncs=total_ncs,
            open_ncs=open_ncs,
            closed_ncs=closed_ncs,
            nc_rate_percentage=nc_rate,
            total_rework_minutes=round(float(total_rework), 1)
        )

    @classmethod
    def get_production_analytics(
        cls,
        db: Session,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        machine_id: Optional[int] = None,
        shift_id: Optional[int] = None,
        customer_id: Optional[int] = None
    ) -> ProductionDashboardResponse:
        query = db.query(ProductionRecord)
        if start_date:
            query = query.filter(ProductionRecord.date >= start_date)
        if end_date:
            query = query.filter(ProductionRecord.date <= end_date)
        if machine_id:
            query = query.filter(ProductionRecord.machine_id == machine_id)
        if shift_id:
            query = query.filter(ProductionRecord.shift_id == shift_id)
        if customer_id:
            query = query.filter(ProductionRecord.customer_id == customer_id)

        records = query.all()
        total_prod = len(records)
        distinct_machines = len(set(r.machine_id for r in records))
        total_minutes = sum(r.total_testing_time for r in records)
        avg_cycle_hrs = round((total_minutes / total_prod / 60.0), 3) if total_prod > 0 else 0.0

        # 1. Daily Trends
        daily_map: Dict[str, Dict[str, Any]] = {}
        for r in records:
            d_str = str(r.date)
            if d_str not in daily_map:
                daily_map[d_str] = {"count": 0, "total_cycle": 0.0}
            daily_map[d_str]["count"] += 1
            daily_map[d_str]["total_cycle"] += r.cycle_time_hours

        daily_trends = [
            TrendItem(
                label=k,
                count=v["count"],
                secondary_value=round(v["total_cycle"] / v["count"], 2) if v["count"] > 0 else 0.0
            ) for k, v in sorted(daily_map.items())
        ]

        # 2. Monthly Trends
        monthly_map: Dict[str, int] = {}
        for r in records:
            m_str = str(r.date)[:7]  # YYYY-MM
            monthly_map[m_str] = monthly_map.get(m_str, 0) + 1

        monthly_trends = [
            TrendItem(label=k, count=v) for k, v in sorted(monthly_map.items())
        ]

        # 3. Machine-Wise Production
        mach_lookup = {m.id: m.machine_code for m in db.query(Machine).all()}
        mach_map: Dict[str, int] = {}
        for r in records:
            code = mach_lookup.get(r.machine_id, f"M-{r.machine_id}")
            mach_map[code] = mach_map.get(code, 0) + 1

        machine_wise = [
            TrendItem(label=k, count=v) for k, v in sorted(mach_map.items(), key=lambda x: x[1], reverse=True)
        ]

        # 4. Shift-Wise Production
        shift_lookup = {s.id: s.shift_name for s in db.query(Shift).all()}
        shift_map: Dict[str, int] = {}
        for r in records:
            name = shift_lookup.get(r.shift_id, f"Shift {r.shift_id}")
            shift_map[name] = shift_map.get(name, 0) + 1

        shift_wise = [
            TrendItem(label=k, count=v) for k, v in sorted(shift_map.items())
        ]

        # 5. Customer-Wise Production
        cust_lookup = {c.id: c.customer_name for c in db.query(Customer).all()}
        cust_map: Dict[str, int] = {}
        for r in records:
            name = cust_lookup.get(r.customer_id, f"Customer {r.customer_id}")
            cust_map[name] = cust_map.get(name, 0) + 1

        cust_wise = [
            TrendItem(label=k, count=v) for k, v in sorted(cust_map.items(), key=lambda x: x[1], reverse=True)
        ]

        return ProductionDashboardResponse(
            total_production=total_prod,
            total_machines_tested=distinct_machines,
            average_cycle_time_hours=avg_cycle_hrs,
            total_testing_minutes=round(total_minutes, 1),
            daily_trends=daily_trends,
            monthly_trends=monthly_trends,
            machine_wise_production=machine_wise,
            shift_wise_production=shift_wise,
            customer_wise_production=cust_wise
        )

    @classmethod
    def get_quality_analytics(
        cls,
        db: Session,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        machine_id: Optional[int] = None
    ) -> QualityDashboardResponse:
        nc_query = db.query(NCRecord)
        if machine_id:
            nc_query = nc_query.filter(NCRecord.machine_id == machine_id)
        if start_date:
            nc_query = nc_query.filter(NCRecord.created_at >= start_date)
        if end_date:
            nc_query = nc_query.filter(NCRecord.created_at <= end_date)

        ncs = nc_query.all()
        total_ncs = len(ncs)

        open_cnt = sum(1 for n in ncs if n.status == NCStatusEnum.OPEN.value)
        prog_cnt = sum(1 for n in ncs if n.status == NCStatusEnum.IN_PROGRESS.value)
        rev_cnt = sum(1 for n in ncs if n.status == NCStatusEnum.UNDER_REVIEW.value)
        closed_cnt = sum(1 for n in ncs if n.status == NCStatusEnum.CLOSED.value)

        # NC rate relative to production
        total_prod = db.query(func.count(ProductionRecord.id)).scalar() or 0
        nc_rate = round((total_ncs / total_prod * 100.0), 2) if total_prod > 0 else 0.0

        # Total rework
        total_rework = sum(
            sum(r.rework_minutes for r in n.rework_records) for n in ncs
        )
        if total_rework == 0:
            total_rework = db.query(func.sum(QualityRecord.rework_minutes)).scalar() or 0.0

        # Category distribution
        cat_map: Dict[str, int] = {}
        for n in ncs:
            cat = n.defect_category or "Unclassified"
            cat_map[cat] = cat_map.get(cat, 0) + 1

        cat_dist = [
            CategoryDistributionItem(
                category=k,
                count=v,
                percentage=round((v / total_ncs * 100.0), 1) if total_ncs > 0 else 0.0
            ) for k, v in sorted(cat_map.items(), key=lambda x: x[1], reverse=True)
        ]

        # Severity distribution
        sev_map: Dict[str, int] = {}
        for n in ncs:
            sev = n.classification or "MAJOR"
            sev_map[sev] = sev_map.get(sev, 0) + 1

        sev_dist = [
            CategoryDistributionItem(
                category=k,
                count=v,
                percentage=round((v / total_ncs * 100.0), 1) if total_ncs > 0 else 0.0
            ) for k, v in sorted(sev_map.items(), key=lambda x: x[1], reverse=True)
        ]

        # Monthly NC trends
        monthly_map: Dict[str, int] = {}
        for n in ncs:
            m_str = str(n.created_at)[:7] if n.created_at else "Unknown"
            monthly_map[m_str] = monthly_map.get(m_str, 0) + 1

        monthly_trends = [
            TrendItem(label=k, count=v) for k, v in sorted(monthly_map.items())
        ]

        # Department distribution
        dept_map: Dict[str, int] = {}
        for n in ncs:
            dept = n.responsible_department or "Unassigned"
            dept_map[dept] = dept_map.get(dept, 0) + 1

        dept_dist = [
            CategoryDistributionItem(
                category=k,
                count=v,
                percentage=round((v / total_ncs * 100.0), 1) if total_ncs > 0 else 0.0
            ) for k, v in sorted(dept_map.items(), key=lambda x: x[1], reverse=True)
        ]

        return QualityDashboardResponse(
            total_ncs=total_ncs,
            open_ncs=open_cnt,
            in_progress_ncs=prog_cnt,
            under_review_ncs=rev_cnt,
            closed_ncs=closed_cnt,
            nc_rate_percentage=nc_rate,
            total_rework_minutes=round(float(total_rework), 1),
            category_distribution=cat_dist,
            severity_distribution=sev_dist,
            monthly_nc_trends=monthly_trends,
            department_distribution=dept_dist
        )

    @classmethod
    def get_machine_performance(cls, db: Session) -> MachineDashboardResponse:
        """Computes comprehensive performance comparison across all registered machines."""
        machines = db.query(Machine).all()
        result: List[MachinePerformanceItem] = []

        for m in machines:
            records = db.query(ProductionRecord).filter(ProductionRecord.machine_id == m.id).all()
            total_tests = len(records)
            pass_tests = sum(1 for r in records if r.test_result == "PASS")
            fail_tests = sum(1 for r in records if r.test_result in ("FAIL", "CONDITIONAL"))
            pass_rate = round((pass_tests / total_tests * 100.0), 1) if total_tests > 0 else 100.0

            total_mins = sum(r.total_testing_time for r in records)
            avg_cycle = round((total_mins / total_tests / 60.0), 2) if total_tests > 0 else 0.0

            # NCs and rework
            nc_count = db.query(func.count(NCRecord.id)).filter(NCRecord.machine_id == m.id).scalar() or 0
            rework_mins = db.query(func.sum(ProductionRecord.rework_time)).filter(ProductionRecord.machine_id == m.id).scalar() or 0.0

            result.append(MachinePerformanceItem(
                machine_id=m.id,
                machine_code=m.machine_code,
                machine_name=m.name,
                total_tests=total_tests,
                pass_tests=pass_tests,
                fail_tests=fail_tests,
                pass_rate_percentage=pass_rate,
                average_cycle_time_hours=avg_cycle,
                total_testing_time_minutes=round(total_mins, 1),
                total_ncs=nc_count,
                total_rework_minutes=round(float(rework_mins), 1)
            ))

        return MachineDashboardResponse(machines=result)

