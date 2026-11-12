from typing import Optional
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.production import (
    ProductionRecordCreate,
    ProductionRecordUpdate,
    ProductionRecordResponse,
    ProductionPaginationResponse,
    ProductionApprovalRequest
)
from app.services.production_service import ProductionService
from app.core.websocket_manager import ws_manager

router = APIRouter()


@router.post("/", response_model=ProductionRecordResponse, status_code=status.HTTP_201_CREATED, summary="Create a new production entry")
async def create_production_record(
    record_in: ProductionRecordCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Submits a new production entry.
    - Validates all 14 mandatory fields
    - Prevents duplicates for the same Machine, Date, and Shift
    - Automatically computes and verifies Total Testing Time and Cycle Time in Hours
    - Creates immutable audit record
    - Broadcasts live WebSocket event
    """
    ip_addr = request.client.host if request.client else "127.0.0.1"
    new_record = ProductionService.create_record(
        db=db,
        record_in=record_in,
        username="operator_suresh",
        user_id=record_in.operator_id,
        role="Operator",
        ip_address=ip_addr
    )
    
    # Broadcast to active dashboard clients
    await ws_manager.broadcast("PRODUCTION_RECORD_CREATED", {
        "id": new_record.id,
        "date": str(new_record.date),
        "machine_id": new_record.machine_id,
        "total_testing_time": new_record.total_testing_time,
        "cycle_time_hours": new_record.cycle_time_hours,
        "test_result": new_record.test_result,
        "nc_raised": new_record.nc_raised
    })

    return ProductionService.get_record_by_id(db, new_record.id)


@router.get("/", response_model=ProductionPaginationResponse, summary="Query and filter production records with pagination")
def list_production_records(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Free text search on Machine or Customer"),
    machine_id: Optional[int] = Query(None, description="Filter by Machine ID"),
    shift_id: Optional[int] = Query(None, description="Filter by Shift ID"),
    customer_id: Optional[int] = Query(None, description="Filter by Customer ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    approval_status: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED)"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated list of production records with comprehensive filtering and search."""
    records, total_count, total_pages = ProductionService.get_records(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        machine_id=machine_id,
        shift_id=shift_id,
        customer_id=customer_id,
        start_date=start_date,
        end_date=end_date,
        approval_status=approval_status
    )
    return ProductionPaginationResponse(
        items=records,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{record_id}", response_model=ProductionRecordResponse, summary="Get single production record")
def get_production_record(record_id: int, db: Session = Depends(get_db)):
    """Fetches full details of a single production record by ID."""
    return ProductionService.get_record_by_id(db, record_id)


@router.put("/{record_id}", response_model=ProductionRecordResponse, summary="Update production record")
async def update_production_record(
    record_id: int,
    update_in: ProductionRecordUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Updates an existing production record.
    Recalculates times and captures audit differences.
    """
    ip_addr = request.client.host if request.client else "127.0.0.1"
    updated = ProductionService.update_record(
        db=db,
        record_id=record_id,
        update_in=update_in,
        username="supervisor_rajesh",
        role="Supervisor",
        ip_address=ip_addr
    )

    await ws_manager.broadcast("PRODUCTION_RECORD_UPDATED", {
        "id": updated.id,
        "total_testing_time": updated.total_testing_time,
        "cycle_time_hours": updated.cycle_time_hours,
        "approval_status": updated.approval_status
    })

    return ProductionService.get_record_by_id(db, updated.id)


@router.patch("/{record_id}/approve", response_model=ProductionRecordResponse, summary="Approve or reject a production entry")
async def approve_production_record(
    record_id: int,
    approval_in: ProductionApprovalRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Supervisor approval workflow.
    - APPROVE marks status APPROVED
    - REJECT marks status REJECTED with mandatory rejection_reason
    """
    ip_addr = request.client.host if request.client else "127.0.0.1"
    approved_rec = ProductionService.approve_or_reject(
        db=db,
        record_id=record_id,
        approval_in=approval_in,
        username="supervisor_rajesh",
        role="Supervisor",
        ip_address=ip_addr
    )

    await ws_manager.broadcast("PRODUCTION_RECORD_APPROVAL", {
        "id": approved_rec.id,
        "action": approval_in.action.upper(),
        "status": approved_rec.approval_status,
        "approved_by_id": approved_rec.approved_by_id
    })

    return ProductionService.get_record_by_id(db, approved_rec.id)

