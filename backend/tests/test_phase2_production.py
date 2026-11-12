import pytest
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal, Base, engine
from app.models.all_models import ProductionRecord, AuditLog


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Clean up any leftover test production records and audit logs
    db.query(ProductionRecord).delete()
    db.query(AuditLog).filter(AuditLog.module == "PRODUCTION").delete()
    db.commit()
    db.close()
    
    with TestClient(app) as c:
        yield c


def test_master_dropdowns(client):
    response = client.get("/api/v1/master/dropdowns")
    assert response.status_code == 200
    data = response.json()
    assert len(data["machines"]) >= 6
    assert len(data["frames"]) >= 7
    assert len(data["shifts"]) >= 3
    assert len(data["customers"]) >= 5
    assert len(data["operators"]) >= 1
    assert len(data["supervisors"]) >= 1


def test_production_record_creation_and_calculations(client):
    today_str = str(date.today())
    payload = {
        "date": today_str,
        "machine_id": 1,
        "frame_id": 1,
        "shift_id": 1,
        "operator_id": 3,
        "supervisor_id": 2,
        "customer_id": 1,
        "static_time": 15.5,
        "mounting_time": 10.0,
        "rotational_time": 25.5,
        "dismantling_time": 9.0,
        "test_result": "PASS",
        "nc_raised": False,
        "rework_time": 0.0,
        "notes": "First test run of the shift"
    }
    
    response = client.post("/api/v1/production/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["date"] == today_str
    
    # Verify calculated values: 15.5 + 10.0 + 25.5 + 9.0 = 60.0 minutes
    assert data["total_testing_time"] == 60.0
    # 60.0 / 60 = 1.0 hour
    assert data["cycle_time_hours"] == 1.0
    assert data["approval_status"] == "PENDING"
    assert data["machine"]["machine_code"] == "M-101"
    assert data["customer"]["customer_code"] == "CUST-ABB"


def test_duplicate_record_prevention(client):
    today_str = str(date.today())
    payload = {
        "date": today_str,
        "machine_id": 1,  # Same machine
        "frame_id": 2,
        "shift_id": 1,    # Same shift
        "operator_id": 3,
        "supervisor_id": 2,
        "customer_id": 2,
        "static_time": 20.0,
        "mounting_time": 10.0,
        "rotational_time": 20.0,
        "dismantling_time": 10.0,
        "test_result": "PASS",
        "nc_raised": False,
        "rework_time": 0.0
    }
    
    # Attempting to submit another active record for the same machine, date, and shift
    response = client.post("/api/v1/production/", json=payload)
    assert response.status_code == 409
    assert "Duplicate Record" in response.json()["detail"]


def test_list_and_filter_production_records(client):
    # Query all
    response = client.get("/api/v1/production/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] >= 1
    assert len(data["items"]) >= 1

    # Filter by machine_id
    response_filt = client.get("/api/v1/production/?machine_id=1")
    assert response_filt.status_code == 200
    assert response_filt.json()["total_count"] >= 1

    # Filter by non-existent machine
    response_empty = client.get("/api/v1/production/?machine_id=9999")
    assert response_empty.status_code == 200
    assert response_empty.json()["total_count"] == 0


def test_get_single_production_record(client):
    # Get first record
    list_res = client.get("/api/v1/production/")
    first_id = list_res.json()["items"][0]["id"]

    response = client.get(f"/api/v1/production/{first_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == first_id
    assert "machine" in data
    assert "customer" in data


def test_update_production_record(client):
    list_res = client.get("/api/v1/production/")
    first_id = list_res.json()["items"][0]["id"]

    update_payload = {
        "rotational_time": 35.5,
        "notes": "Updated rotational time after recalibration"
    }
    response = client.put(f"/api/v1/production/{first_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["rotational_time"] == 35.5
    # Recalculated total: 15.5 + 10.0 + 35.5 + 9.0 = 70.0
    assert data["total_testing_time"] == 70.0
    # 70.0 / 60 = 1.1667
    assert abs(data["cycle_time_hours"] - 1.1667) < 0.001


def test_approval_workflow(client):
    list_res = client.get("/api/v1/production/")
    first_id = list_res.json()["items"][0]["id"]

    # 1. Reject without reason should fail validation
    invalid_reject = {
        "action": "REJECT",
        "supervisor_id": 2
    }
    res_err = client.patch(f"/api/v1/production/{first_id}/approve", json=invalid_reject)
    assert res_err.status_code == 422

    # 2. Reject with reason
    valid_reject = {
        "action": "REJECT",
        "supervisor_id": 2,
        "rejection_reason": "High vibration noted during rotational phase"
    }
    res_rej = client.patch(f"/api/v1/production/{first_id}/approve", json=valid_reject)
    assert res_rej.status_code == 200
    assert res_rej.json()["approval_status"] == "REJECTED"
    assert res_rej.json()["rejection_reason"] == "High vibration noted during rotational phase"

    # 3. Approve
    valid_approve = {
        "action": "APPROVE",
        "supervisor_id": 2
    }
    res_app = client.patch(f"/api/v1/production/{first_id}/approve", json=valid_approve)
    assert res_app.status_code == 200
    assert res_app.json()["approval_status"] == "APPROVED"
    assert res_app.json()["approved_by_id"] == 2


def test_audit_logs_captured():
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).filter(AuditLog.module == "PRODUCTION").all()
        assert len(logs) >= 3
        actions = [l.action for l in logs]
        assert "CREATE" in actions
        assert "UPDATE" in actions
        assert "APPROVE" in actions or "REJECT" in actions
    finally:
        db.close()
