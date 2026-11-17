import io
import pytest
import pandas as pd
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal, Base, engine
from app.models.all_models import (
    ProductionRecord, QualityRecord, NCRecord, ImportHistory, ImportError, AuditLog
)


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Clean up test migration batches
    db.query(ImportError).delete()
    db.query(ImportHistory).delete()
    db.commit()
    db.close()

    with TestClient(app) as c:
        yield c


def _create_excel_bytes(rows: list, sheet_name: str = "Sheet1") -> bytes:
    """Helper to convert list of dict rows to in-memory Excel bytes."""
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buf.seek(0)
    return buf.getvalue()


def test_valid_production_excel_import(client):
    today_str = "2026-10-15"
    test_rows = [
        {
            "Date": today_str,
            "Machine Number": "M-101",
            "Frame": "Frame 63",
            "Shift": "Shift A",
            "Customer": "ABB Power & Industrial Grids",
            "Operator": "Suresh M. (Lead Operator)",
            "Supervisor": "Rajesh K. (Production Supervisor)",
            "Static Testing Time": 12.0,
            "Mounting Time": 10.0,
            "Rotational Testing Time": 20.0,
            "Dismantling Time": 8.0,
            "Test Result": "PASS",
            "NC Raised": "No",
            "Rework Time": 0.0,
            "Notes": "Import test motor batch 01"
        },
        {
            "Date": today_str,
            "Machine Number": "M-102",
            "Frame": "Frame 71",
            "Shift": "Shift A",
            "Customer": "Siemens Energy India",
            "Operator": "Suresh M. (Lead Operator)",
            "Supervisor": "Rajesh K. (Production Supervisor)",
            "Static Testing Time": 15.0,
            "Mounting Time": 12.0,
            "Rotational Testing Time": 25.0,
            "Dismantling Time": 8.0,
            "Test Result": "PASS",
            "NC Raised": "No",
            "Rework Time": 0.0,
            "Notes": "Import test motor batch 02"
        }
    ]

    excel_data = _create_excel_bytes(test_rows, sheet_name="Production")
    
    # 1. Upload & Validate
    response = client.post(
        "/api/v1/import/upload",
        files={"file": ("Production.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"file_type": "PRODUCTION"}
    )
    assert response.status_code == 200
    val_data = response.json()
    assert val_data["valid_count"] == 2
    assert val_data["rejected_count"] == 0
    assert val_data["can_commit"] is True
    batch_id = val_data["batch_id"]

    # 2. Confirm Commit
    confirm_res = client.post("/api/v1/import/confirm", json={
        "batch_id": batch_id,
        "user_id": 1,
        "username": "admin",
        "role": "Administrator"
    })
    assert confirm_res.status_code == 200
    conf_data = confirm_res.json()
    assert conf_data["imported_records_count"] == 2
    assert conf_data["status"] == "COMPLETED"


def test_duplicate_and_invalid_date_rejection(client):
    test_rows = [
        # Valid row
        {
            "Date": "2026-10-20",
            "Machine Number": "M-103",
            "Frame": "Frame 80",
            "Shift": "Shift B",
            "Static Testing Time": 15.0,
            "Mounting Time": 10.0,
            "Rotational Testing Time": 20.0,
            "Dismantling Time": 10.0
        },
        # Duplicate row within same spreadsheet
        {
            "Date": "2026-10-20",
            "Machine Number": "M-103",
            "Frame": "Frame 80",
            "Shift": "Shift B",
            "Static Testing Time": 15.0,
            "Mounting Time": 10.0,
            "Rotational Testing Time": 20.0,
            "Dismantling Time": 10.0
        },
        # Invalid corrupt date
        {
            "Date": "NotADateString",
            "Machine Number": "M-201",
            "Frame": "Frame 90",
            "Shift": "Shift C",
            "Static Testing Time": 10.0,
            "Mounting Time": 10.0,
            "Rotational Testing Time": 10.0,
            "Dismantling Time": 10.0
        }
    ]

    excel_data = _create_excel_bytes(test_rows)
    response = client.post(
        "/api/v1/import/upload",
        files={"file": ("Production_Duplicates.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"file_type": "PRODUCTION"}
    )
    assert response.status_code == 200
    val_data = response.json()
    assert val_data["valid_count"] == 1
    assert val_data["rejected_count"] == 2
    assert val_data["duplicate_count"] == 1

    err_types = [e["error_type"] for e in val_data["rejected_rows"]]
    assert "DUPLICATE_IN_FILE" in err_types
    assert "INVALID_DATE" in err_types


def test_missing_machine_number_rejection(client):
    test_rows = [
        {
            "Date": "2026-10-22",
            "Machine Number": "M-NON-EXISTENT-999",
            "Shift": "Shift A",
            "Static Testing Time": 10.0,
            "Mounting Time": 10.0,
            "Rotational Testing Time": 10.0,
            "Dismantling Time": 10.0
        }
    ]

    excel_data = _create_excel_bytes(test_rows)
    response = client.post(
        "/api/v1/import/upload",
        files={"file": ("Bad_Machine.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"file_type": "PRODUCTION"}
    )
    assert response.status_code == 200
    val_data = response.json()
    assert val_data["valid_count"] == 0
    assert val_data["rejected_count"] == 1
    assert val_data["rejected_rows"][0]["error_type"] == "UNKNOWN_MACHINE"


def test_invalid_numeric_values_rejection(client):
    test_rows = [
        {
            "Date": "2026-10-25",
            "Machine Number": "M-101",
            "Shift": "Shift A",
            "Static Testing Time": -50.0,  # Negative time
            "Mounting Time": "CorruptedText", # Non-numeric text
            "Rotational Testing Time": 10.0,
            "Dismantling Time": 10.0
        }
    ]

    excel_data = _create_excel_bytes(test_rows)
    response = client.post(
        "/api/v1/import/upload",
        files={"file": ("Bad_Numeric.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"file_type": "PRODUCTION"}
    )
    assert response.status_code == 200
    val_data = response.json()
    assert val_data["valid_count"] == 0
    assert val_data["rejected_count"] == 1
    assert val_data["rejected_rows"][0]["error_type"] == "INVALID_NUMERIC"


def test_quality_nc_excel_import(client):
    test_rows = [
        {
            "Date": "2026-10-18",
            "Machine Number": "M-101",
            "Defect Description": "Vibration harmonics exceeding limit on test bench",
            "Defect Category": "Mechanical",
            "Responsible Department": "Maintenance",
            "Severity": "HIGH",
            "Classification": "MAJOR",
            "Rework Minutes": 40.0,
            "Status": "IN_PROGRESS",
            "Root Cause": "Loose locking nut on sensor plate"
        }
    ]

    excel_data = _create_excel_bytes(test_rows, sheet_name="Quality_Tracking")
    response = client.post(
        "/api/v1/import/upload",
        files={"file": ("Quality_NC_s_tracking.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"file_type": "QUALITY"}
    )
    assert response.status_code == 200
    val_data = response.json()
    assert val_data["valid_count"] == 1
    batch_id = val_data["batch_id"]

    confirm_res = client.post("/api/v1/import/confirm", json={
        "batch_id": batch_id,
        "user_id": 1,
        "username": "admin",
        "role": "Administrator"
    })
    assert confirm_res.status_code == 200
    assert confirm_res.json()["imported_records_count"] == 1


def test_import_history_and_errors_report(client):
    # Query history
    res = client.get("/api/v1/import/history")
    assert res.status_code == 200
    history = res.json()
    assert len(history) >= 2

    first_id = history[0]["id"]
    # Query errors list
    err_res = client.get(f"/api/v1/import/{first_id}/errors")
    assert err_res.status_code == 200


def test_export_production_excel(client):
    res = client.get("/api/v1/export/production")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    # Read bytes with pandas to ensure it's a valid Excel spreadsheet
    df = pd.read_excel(io.BytesIO(res.content))
    assert not df.empty
    assert "Record ID" in df.columns
    assert "Machine Code" in df.columns
    assert "Cycle Time (hours)" in df.columns


def test_export_quality_excel(client):
    res = client.get("/api/v1/export/quality")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    df = pd.read_excel(io.BytesIO(res.content))
    assert not df.empty
    assert "NC Number" in df.columns
    assert "Defect Category" in df.columns

