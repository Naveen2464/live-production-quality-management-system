import pytest
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal, Base, engine
from app.models.all_models import ProductionRecord, NCRecord, QualityRecord, Machine


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def test_dashboard_summary_metrics(client):
    res = client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_machines_tested" in data
    assert "total_production_records" in data
    assert "average_cycle_time_hours" in data
    assert "total_ncs" in data
    assert "open_ncs" in data
    assert "closed_ncs" in data
    assert "nc_rate_percentage" in data
    assert "total_rework_minutes" in data
    assert isinstance(data["average_cycle_time_hours"], float)
    assert isinstance(data["total_rework_minutes"], float)


def test_production_dashboard_analytics(client):
    res = client.get("/api/v1/dashboard/production")
    assert res.status_code == 200
    data = res.json()
    assert "total_production" in data
    assert "daily_trends" in data
    assert "monthly_trends" in data
    assert "machine_wise_production" in data
    assert "shift_wise_production" in data
    assert "customer_wise_production" in data


def test_production_dashboard_filters(client):
    # Filter by existing machine
    res = client.get("/api/v1/dashboard/production?machine_id=1")
    assert res.status_code == 200
    data = res.json()
    assert "total_production" in data

    # Filter by non-existent machine returns 0 safely without error
    res_empty = client.get("/api/v1/dashboard/production?machine_id=99999")
    assert res_empty.status_code == 200
    empty_data = res_empty.json()
    assert empty_data["total_production"] == 0
    assert empty_data["average_cycle_time_hours"] == 0.0

    # Filter by date range
    res_date = client.get("/api/v1/dashboard/production?start_date=2026-01-01&end_date=2026-12-31")
    assert res_date.status_code == 200


def test_quality_dashboard_analytics(client):
    res = client.get("/api/v1/dashboard/quality")
    assert res.status_code == 200
    data = res.json()
    assert "total_ncs" in data
    assert "open_ncs" in data
    assert "closed_ncs" in data
    assert "category_distribution" in data
    assert "severity_distribution" in data
    assert "monthly_nc_trends" in data
    assert "department_distribution" in data
    assert isinstance(data["category_distribution"], list)


def test_quality_dashboard_filters(client):
    res = client.get("/api/v1/dashboard/quality?machine_id=1")
    assert res.status_code == 200
    data = res.json()
    assert "total_ncs" in data


def test_machine_performance_comparison(client):
    res = client.get("/api/v1/dashboard/machines")
    assert res.status_code == 200
    data = res.json()
    assert "machines" in data
    assert len(data["machines"]) >= 6
    
    first_machine = data["machines"][0]
    assert "machine_code" in first_machine
    assert "total_tests" in first_machine
    assert "pass_rate_percentage" in first_machine
    assert "average_cycle_time_hours" in first_machine
    assert "total_ncs" in first_machine
    assert "total_rework_minutes" in first_machine

