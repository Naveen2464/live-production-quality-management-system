"""
Backend Test Suite: test_phase6_powerbi.py
Validates Phase 6 Star Schema Reporting Views, Dimensional Integrity,
and DAX Measure Equivalency against underlying operational tables.
"""
import pytest
from sqlalchemy import text
from app.db.session import SessionLocal, engine

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_reporting_views_exist(db_session):
    """Verify all 3 Fact Views and 8 Dimension Views are queryable in database."""
    views = [
        "vw_dim_date",
        "vw_dim_machine",
        "vw_dim_customer",
        "vw_dim_frame",
        "vw_dim_shift",
        "vw_dim_personnel",
        "vw_dim_defect_category",
        "vw_dim_severity",
        "vw_fact_production",
        "vw_fact_quality_nc",
        "vw_fact_rework"
    ]
    for view_name in views:
        result = db_session.execute(text(f"SELECT COUNT(*) FROM {view_name}")).scalar()
        assert result is not None
        assert result >= 0

def test_date_dimension_series(db_session):
    """Verify vw_dim_date contains continuous dates with valid integer date_key."""
    row = db_session.execute(text("""
        SELECT date_key, full_date, calendar_year, quarter_name, month_name, is_weekend
        FROM vw_dim_date
        WHERE full_date = '2026-01-01'
    """)).fetchone()
    assert row is not None
    assert row[0] == 20260101
    assert row[2] == 2026
    assert row[3] == "Q1"
    assert row[4] == "January"

def test_production_fact_reconciliation(db_session):
    """Verify vw_fact_production matches production_records operational figures exactly."""
    op_data = db_session.execute(text("""
        SELECT 
            COUNT(*) as total_runs,
            SUM(CASE WHEN UPPER(approval_status) = 'APPROVED' THEN 1 ELSE 0 END) as approved_runs,
            SUM(CASE WHEN UPPER(test_result) = 'PASS' THEN 1 ELSE 0 END) as pass_runs
        FROM production_records
    """)).fetchone()

    view_data = db_session.execute(text("""
        SELECT 
            COUNT(*) as total_runs,
            SUM(is_approved) as approved_runs,
            SUM(is_pass) as pass_runs
        FROM vw_fact_production
    """)).fetchone()

    assert op_data[0] == view_data[0], "Total production runs mismatch"
    assert op_data[1] == view_data[1], "Approved runs mismatch"
    assert op_data[2] == view_data[2], "Pass runs mismatch"

def test_quality_fact_reconciliation(db_session):
    """Verify vw_fact_quality_nc matches nc_records counts and status flags."""
    op_ncs = db_session.execute(text("""
        SELECT 
            COUNT(*) as total_ncs,
            SUM(CASE WHEN UPPER(status) = 'CLOSED' THEN 1 ELSE 0 END) as closed_ncs
        FROM nc_records
    """)).fetchone()

    view_ncs = db_session.execute(text("""
        SELECT 
            COUNT(*) as total_ncs,
            SUM(is_closed) as closed_ncs
        FROM vw_fact_quality_nc
    """)).fetchone()

    assert op_ncs[0] == view_ncs[0], "Total NC count mismatch"
    assert op_ncs[1] == view_ncs[1], "Closed NC count mismatch"

def test_rework_fact_reconciliation(db_session):
    """Verify vw_fact_rework matches rework_records minutes and task counts."""
    op_rw = db_session.execute(text("""
        SELECT 
            COUNT(*) as total_tasks,
            COALESCE(SUM(rework_minutes), 0.0) as total_min
        FROM rework_records
    """)).fetchone()

    view_rw = db_session.execute(text("""
        SELECT 
            COUNT(*) as total_tasks,
            COALESCE(SUM(rework_minutes), 0.0) as total_min
        FROM vw_fact_rework
    """)).fetchone()

    assert op_rw[0] == view_rw[0], "Total rework tasks mismatch"
    assert float(op_rw[1]) == pytest.approx(float(view_rw[1]), 0.01), "Total rework minutes mismatch"

def test_dax_formula_equivalency(db_session):
    """Verify DAX measures produce identical values when evaluated via SQL equivalent expressions."""
    # Test DAX Total Testing Hours = DIVIDE(SUM(Total_Testing_Time_Minutes), 60)
    testing_hours = db_session.execute(text("""
        SELECT ROUND(SUM(total_testing_time_minutes) / 60.0, 4)
        FROM vw_fact_production
    """)).scalar()
    
    op_testing_hours = db_session.execute(text("""
        SELECT ROUND(SUM(total_testing_time) / 60.0, 4)
        FROM production_records
    """)).scalar()
    
    assert float(testing_hours) == pytest.approx(float(op_testing_hours), 0.001)

