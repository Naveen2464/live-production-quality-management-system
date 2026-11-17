from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd
import io

from app.db.session import get_db
from app.schemas.migration import (
    ImportValidateResponse, ImportConfirmRequest, ImportConfirmResponse,
    ImportHistoryResponse, ImportErrorItem
)
from app.services.migration_service import MigrationService
from app.core.websocket_manager import ws_manager

router = APIRouter()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB Limit
ALLOWED_EXTENSIONS = (".xlsx", ".xls")


@router.post("/upload", response_model=ImportValidateResponse, summary="Upload and validate Excel spreadsheet")
async def upload_and_validate_excel(
    file: UploadFile = File(..., description="Excel workbook (Production.xlsx or Quality_NC_s_tracking.xlsx)"),
    file_type: str = Form("PRODUCTION", description="Workbook type: PRODUCTION or QUALITY"),
    db: Session = Depends(get_db)
):
    """
    Validates an Excel workbook using Pandas.
    - Inspects headers, parses dates, validates machines and numbers.
    - Detects duplicates within spreadsheet and against database.
    - Returns preview of valid records and list of rejected rows with explanations.
    - Zero data loss: invalid records are reported with row number and reason.
    """
    # 1. Security & Extension check
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file.filename}'. Only .xlsx and .xls files are permitted."
        )

    # 2. Read contents safely
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum permitted limit (20 MB)."
        )

    # 3. Validate with Pandas engine
    validation_res = MigrationService.validate_excel_file(
        db=db,
        file_bytes=contents,
        file_name=file.filename,
        file_type=file_type.upper()
    )

    return validation_res


@router.post("/confirm", response_model=ImportConfirmResponse, summary="Confirm and commit validated import batch into PostgreSQL")
async def confirm_import_batch(
    confirm_in: ImportConfirmRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Executes database insertion of a validated batch in an atomic transaction.
    Logs import summary and saves rejected records to import_errors table.
    """
    ip_addr = request.client.host if request.client else "127.0.0.1"
    res = MigrationService.confirm_import(
        db=db,
        batch_id=confirm_in.batch_id,
        user_id=confirm_in.user_id,
        username=confirm_in.username,
        role=confirm_in.role,
        ip_address=ip_addr
    )

    # Broadcast notification to dashboard clients
    await ws_manager.broadcast("DATA_IMPORT_COMPLETED", {
        "import_history_id": res.import_history_id,
        "file_name": res.file_name,
        "file_type": res.file_type,
        "imported_records": res.imported_records_count,
        "rejected_records": res.rejected_records_count
    })

    return res


@router.get("/history", response_model=List[ImportHistoryResponse], summary="Get history of past spreadsheet migrations")
def list_import_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    return MigrationService.get_import_history(db=db, limit=limit)


@router.get("/{history_id}/errors", response_model=List[ImportErrorItem], summary="Get rejected rows and reasons for an import batch")
def get_import_errors(history_id: int, db: Session = Depends(get_db)):
    errs = MigrationService.get_import_errors(db=db, history_id=history_id)
    return [
        ImportErrorItem(
            row_number=e.row_number,
            error_type=e.error_type,
            field_name=e.field_name,
            error_message=e.error_message,
            raw_data=e.raw_data
        ) for e in errs
    ]


@router.get("/{history_id}/errors/download", summary="Download rejected rows report as CSV")
def download_import_errors_csv(history_id: int, db: Session = Depends(get_db)):
    errs = MigrationService.get_import_errors(db=db, history_id=history_id)
    if not errs:
        raise HTTPException(status_code=404, detail="No error records found for this batch.")

    rows = []
    for e in errs:
        rows.append({
            "Row Number": e.row_number,
            "Error Type": e.error_type,
            "Field Name": e.field_name or "",
            "Error Message": e.error_message,
            "Raw Row Data": str(e.raw_data or "")
        })

    df = pd.DataFrame(rows)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)

    return StreamingResponse(
        io.BytesIO(csv_buf.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=rejected_rows_batch_{history_id}.csv"}
    )


# -------------------------------------------------------------
# EXCEL EXPORT ENDPOINTS
# -------------------------------------------------------------
@router.get("/export/production", summary="Export production records to an Excel workbook")
def export_production_excel(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    machine_id: Optional[int] = Query(None),
    status_val: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    excel_stream = MigrationService.export_production_to_excel(
        db=db,
        start_date=start_date,
        end_date=end_date,
        machine_id=machine_id,
        status_val=status_val
    )
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Production_Records_Export.xlsx"}
    )


@router.get("/export/quality", summary="Export quality and NC records to an Excel workbook")
def export_quality_excel(
    status_val: Optional[str] = Query(None, alias="status"),
    classification: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    excel_stream = MigrationService.export_quality_to_excel(
        db=db,
        status_val=status_val,
        classification=classification
    )
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Quality_NC_Records_Export.xlsx"}
    )

