import pytest
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal, Base, engine
from app.models.all_models import QualityRecord, NCRecord, ReworkRecord, ProductionRecord, AuditLog


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Clean up test quality records, NCs, reworks and audit logs
    db.query(ReworkRecord).delete()
    db.query(NCRecord).delete()
    db.query(QualityRecord).delete()
    db.query(AuditLog).filter(AuditLog.module.in_(["QUALITY", "NC", "REWORK"])).delete()
    db.commit()
    db.close()

    with TestClient(app) as c:
        yield c


def test_quality_record_creation_with_auto_nc(client):
    payload = {
        "machine_id": 1,
        "defect_description": "Excessive bearing temperature rise during full load run (>85°C)",
        "defect_category": "Mechanical",
        "date_of_occurrence": str(date.today()),
        "responsible_department": "Maintenance",
        "severity": "HIGH",
        "rework_minutes": 30.0,
        "create_nc": True,
        "nc_classification": "CRITICAL"
    }

    res = client.post("/api/v1/quality/", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["defect_category"] == "Mechanical"
    assert data["severity"] == "HIGH"
    assert data["nc_number"] is not None
    assert data["nc_number"].startswith("NC-")

    # Verify audit log was recorded for QUALITY and NC
    db = SessionLocal()
    try:
        q_audit = db.query(AuditLog).filter(AuditLog.module == "QUALITY", AuditLog.action == "CREATE").first()
        nc_audit = db.query(AuditLog).filter(AuditLog.module == "NC", AuditLog.action == "CREATE").first()
        assert q_audit is not None
        assert nc_audit is not None
    finally:
        db.close()


def test_quality_record_linked_to_production(client):
    # 1. Create a production record first
    prod_payload = {
        "date": str(date.today()),
        "machine_id": 2,
        "frame_id": 2,
        "shift_id": 2,
        "operator_id": 3,
        "supervisor_id": 2,
        "customer_id": 2,
        "static_time": 10.0,
        "mounting_time": 10.0,
        "rotational_time": 20.0,
        "dismantling_time": 10.0,
        "test_result": "FAIL",
        "nc_raised": False,
        "rework_time": 0.0
    }
    prod_res = client.post("/api/v1/production/", json=prod_payload)
    assert prod_res.status_code == 201
    prod_id = prod_res.json()["id"]

    # 2. Log quality issue linked to this production run
    q_payload = {
        "production_record_id": prod_id,
        "machine_id": 2,
        "defect_description": "Phase unbalance detected during rotational test",
        "defect_category": "Electrical",
        "date_of_occurrence": str(date.today()),
        "responsible_department": "Assembly",
        "severity": "MEDIUM",
        "rework_minutes": 25.0,
        "create_nc": True
    }
    q_res = client.post("/api/v1/quality/", json=q_payload)
    assert q_res.status_code == 201

    # 3. Verify production record nc_raised and rework_time synchronized
    updated_prod = client.get(f"/api/v1/production/{prod_id}").json()
    assert updated_prod["nc_raised"] is True
    assert updated_prod["rework_time"] == 25.0


def test_nc_workflow_valid_transitions(client):
    # Create NC directly
    nc_payload = {
        "machine_id": 3,
        "title": "Rotor Dynamic Imbalance on Line 2",
        "description": "High frequency vibration exceeds ISO 10816 threshold (4.5 mm/s RMS).",
        "defect_category": "Mechanical",
        "classification": "MAJOR",
        "responsible_department": "Maintenance",
        "quality_engineer_id": 4
    }
    nc_res = client.post("/api/v1/quality/nc", json=nc_payload)
    assert nc_res.status_code == 201
    nc_id = nc_res.json()["id"]
    assert nc_res.json()["status"] == "OPEN"

    # Step 1: OPEN -> IN_PROGRESS
    t1 = client.patch(f"/api/v1/quality/nc/{nc_id}/status", json={
        "target_status": "IN_PROGRESS",
        "user_id": 4,
        "user_role": "Quality Engineer"
    })
    assert t1.status_code == 200
    assert t1.json()["status"] == "IN_PROGRESS"

    # Step 2: Document Root Cause & Corrective Action
    rca_res = client.put(f"/api/v1/quality/nc/{nc_id}", json={
        "root_cause": "Improper balancing weight position on DE side rotor sleeve.",
        "corrective_action": "Replaced balancing ring and calibrated on dynamic balancing rig.",
        "preventive_action": "Tightened torque check SOP in assembly step 4."
    })
    assert rca_res.status_code == 200
    assert rca_res.json()["root_cause"] is not None

    # Step 3: IN_PROGRESS -> UNDER_REVIEW
    t2 = client.patch(f"/api/v1/quality/nc/{nc_id}/status", json={
        "target_status": "UNDER_REVIEW",
        "user_id": 4,
        "user_role": "Quality Engineer"
    })
    assert t2.status_code == 200
    assert t2.json()["status"] == "UNDER_REVIEW"

    # Step 4: UNDER_REVIEW -> CLOSED by Quality Engineer
    t3 = client.patch(f"/api/v1/quality/nc/{nc_id}/status", json={
        "target_status": "CLOSED",
        "user_id": 4,
        "user_role": "Quality Engineer",
        "closure_notes": "Vibration re-test passed at 1.1 mm/s RMS. Verified safe for dispatch."
    })
    assert t3.status_code == 200
    assert t3.json()["status"] == "CLOSED"
    assert t3.json()["closed_at"] is not None
    assert t3.json()["closed_by_id"] == 4


def test_nc_workflow_invalid_transition_rejection(client):
    # Create fresh NC in OPEN status
    nc_payload = {
        "machine_id": 4,
        "title": "Stator Winding Insulation Low Megger Value",
        "description": "Insulation resistance below 5 Megohms at 500V DC.",
        "defect_category": "Electrical",
        "classification": "CRITICAL",
        "responsible_department": "Production",
        "quality_engineer_id": 4
    }
    nc_res = client.post("/api/v1/quality/nc", json=nc_payload)
    nc_id = nc_res.json()["id"]

    # Attempt OPEN -> CLOSED directly (Must be rejected)
    bad_jump = client.patch(f"/api/v1/quality/nc/{nc_id}/status", json={
        "target_status": "CLOSED",
        "user_id": 4,
        "user_role": "Quality Engineer",
        "closure_notes": "Attempting fast closure without investigation"
    })
    assert bad_jump.status_code == 400
    assert "Invalid Workflow Transition" in bad_jump.json()["detail"]

    # Attempt OPEN -> UNDER_REVIEW directly (Must be rejected)
    bad_jump2 = client.patch(f"/api/v1/quality/nc/{nc_id}/status", json={
        "target_status": "UNDER_REVIEW",
        "user_id": 4,
        "user_role": "Quality Engineer"
    })
    assert bad_jump2.status_code == 400


def test_nc_workflow_role_permission_enforcement(client):
    # Create fresh NC and advance to UNDER_REVIEW
    nc_res = client.post("/api/v1/quality/nc", json={
        "machine_id": 1,
        "title": "Terminal Box Gasket Misalignment",
        "description": "IP55 ingress seal violated due to twisted gasket.",
        "defect_category": "Frame Defect",
        "classification": "MINOR",
        "responsible_department": "Assembly",
        "quality_engineer_id": 4
    })
    nc_id = nc_res.json()["id"]

    client.patch(f"/api/v1/quality/nc/{nc_id}/status", json={
        "target_status": "IN_PROGRESS",
        "user_id": 4,
        "user_role": "Quality Engineer"
    })
    client.patch(f"/api/v1/quality/nc/{nc_id}/status", json={
        "target_status": "UNDER_REVIEW",
        "user_id": 4,
        "user_role": "Quality Engineer"
    })

    # 1. Operator attempts closure -> 422 or 403
    op_attempt = client.patch(f"/api/v1/quality/nc/{nc_id}/status", json={
        "target_status": "CLOSED",
        "user_id": 3,
        "user_role": "Operator",
        "closure_notes": "Operator sign off"
    })
    assert op_attempt.status_code in [400, 403, 422]

    # 2. Supervisor attempts closure -> 422 or 403 (Only QE or Admin permitted)
    sup_attempt = client.patch(f"/api/v1/quality/nc/{nc_id}/status", json={
        "target_status": "CLOSED",
        "user_id": 2,
        "user_role": "Supervisor",
        "closure_notes": "Supervisor sign off"
    })
    assert sup_attempt.status_code in [400, 403, 422]

    # 3. Administrator attempts closure with valid notes -> Success
    admin_attempt = client.patch(f"/api/v1/quality/nc/{nc_id}/status", json={
        "target_status": "CLOSED",
        "user_id": 1,
        "user_role": "Administrator",
        "closure_notes": "Gasket replaced and air leak test verified by Quality Lead."
    })
    assert admin_attempt.status_code == 200
    assert admin_attempt.json()["status"] == "CLOSED"


def test_rework_record_tracking_and_production_sync(client):
    # Create NC
    nc_res = client.post("/api/v1/quality/nc", json={
        "machine_id": 5,
        "title": "Shaft Runout Correction Needed",
        "description": "Shaft runout exceeds tolerance by 0.03mm.",
        "defect_category": "Mechanical",
        "classification": "MAJOR",
        "responsible_department": "Maintenance",
        "quality_engineer_id": 4
    })
    nc_id = nc_res.json()["id"]

    # Log Rework
    rework_payload = {
        "nc_record_id": nc_id,
        "machine_id": 5,
        "rework_minutes": 45.0,
        "rework_description": "Skimmed shaft extension on lathe machine to true up runout.",
        "rework_done_by_id": 3,
        "completion_date": str(date.today()),
        "rework_status": "COMPLETED",
        "notes": "Runout reduced to 0.008mm (spec < 0.012mm)"
    }
    r_res = client.post("/api/v1/quality/rework", json=rework_payload)
    assert r_res.status_code == 201
    rework_id = r_res.json()["id"]
    assert r_res.json()["rework_minutes"] == 45.0

    # Verify status verification signoff
    verify_res = client.patch(f"/api/v1/quality/rework/{rework_id}/status", json={
        "rework_status": "VERIFIED",
        "verified_by_id": 4,
        "notes": "Verified with dial gauge indicator."
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["rework_status"] == "VERIFIED"

    # Verify NC detail now shows total rework
    nc_detail = client.get(f"/api/v1/quality/nc/{nc_id}").json()
    assert nc_detail["total_rework_minutes"] == 45.0
    assert len(nc_detail["rework_records"]) == 1

