from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.quality import (
    QualityRecordCreate, QualityRecordResponse,
    NCRecordCreate, NCRecordUpdate, NCRecordResponse, NCPaginationResponse,
    NCStatusTransitionRequest,
    ReworkRecordCreate, ReworkRecordResponse, ReworkStatusUpdate
)
from app.services.quality_service import QualityService
from app.core.websocket_manager import ws_manager

router = APIRouter()


# -------------------------------------------------------------
# QUALITY RECORDS ENDPOINTS
# -------------------------------------------------------------
@router.post("/", response_model=QualityRecordResponse, status_code=status.HTTP_201_CREATED, summary="Log a quality incident/defect")
async def create_quality_record(
    record_in: QualityRecordCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Logs a quality defect. If create_nc=True, automatically spawns a formal NC case.
    Synchronizes NC Raised flag and rework time on linked production runs.
    """
    ip_addr = request.client.host if request.client else "127.0.0.1"
    q_rec, nc_rec = QualityService.create_quality_record(
        db=db,
        record_in=record_in,
        username="qe_priya",
        user_id=4,
        role="Quality Engineer",
        ip_address=ip_addr
    )

    # Broadcast WebSocket notification
    await ws_manager.broadcast("QUALITY_RECORD_CREATED", {
        "id": q_rec.id,
        "machine_id": q_rec.machine_id,
        "defect_category": q_rec.defect_category,
        "severity": q_rec.severity,
        "nc_number": nc_rec.nc_number if nc_rec else None
    })

    if nc_rec:
        await ws_manager.broadcast("NC_RECORD_CREATED", {
            "id": nc_rec.id,
            "nc_number": nc_rec.nc_number,
            "status": nc_rec.status,
            "classification": nc_rec.classification
        })

    return QualityRecordResponse(
        id=q_rec.id,
        production_record_id=q_rec.production_record_id,
        machine_id=q_rec.machine_id,
        defect_description=q_rec.defect_description,
        defect_category=q_rec.defect_category,
        date_of_occurrence=q_rec.date_of_occurrence,
        responsible_department=q_rec.responsible_department,
        severity=q_rec.severity,
        rework_minutes=q_rec.rework_minutes,
        created_by_id=q_rec.created_by_id,
        created_at=q_rec.created_at,
        updated_at=q_rec.updated_at,
        machine_code=q_rec.machine.machine_code if q_rec.machine else None,
        machine_name=q_rec.machine.name if q_rec.machine else None,
        nc_number=nc_rec.nc_number if nc_rec else None
    )


@router.get("/", response_model=List[QualityRecordResponse], summary="List quality defect records")
def list_quality_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    machine_id: Optional[int] = Query(None),
    defect_category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    records, _, _ = QualityService.get_quality_records(
        db=db,
        page=page,
        page_size=page_size,
        machine_id=machine_id,
        defect_category=defect_category,
        severity=severity
    )
    result = []
    for q in records:
        result.append(QualityRecordResponse(
            id=q.id,
            production_record_id=q.production_record_id,
            machine_id=q.machine_id,
            defect_description=q.defect_description,
            defect_category=q.defect_category,
            date_of_occurrence=q.date_of_occurrence,
            responsible_department=q.responsible_department,
            severity=q.severity,
            rework_minutes=q.rework_minutes,
            created_by_id=q.created_by_id,
            created_at=q.created_at,
            updated_at=q.updated_at,
            machine_code=q.machine.machine_code if q.machine else None,
            machine_name=q.machine.name if q.machine else None,
            nc_number=q.nc_record.nc_number if q.nc_record else None
        ))
    return result


# -------------------------------------------------------------
# NON-CONFORMANCE (NC) ENDPOINTS
# -------------------------------------------------------------
@router.post("/nc", response_model=NCRecordResponse, status_code=status.HTTP_201_CREATED, summary="Create an NC ticket directly")
async def create_nc_record(
    nc_in: NCRecordCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    ip_addr = request.client.host if request.client else "127.0.0.1"
    nc = QualityService.create_nc_record(
        db=db,
        nc_in=nc_in,
        username="qe_priya",
        user_id=nc_in.quality_engineer_id,
        role="Quality Engineer",
        ip_address=ip_addr
    )

    await ws_manager.broadcast("NC_RECORD_CREATED", {
        "id": nc.id,
        "nc_number": nc.nc_number,
        "status": nc.status
    })

    return QualityService.get_nc_by_id(db, nc.id)


@router.get("/nc", response_model=NCPaginationResponse, summary="Query and filter NC records")
def list_ncs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status_val: Optional[str] = Query(None, alias="status"),
    classification: Optional[str] = Query(None),
    machine_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    records, total_count, total_pages = QualityService.get_ncs(
        db=db,
        page=page,
        page_size=page_size,
        status_val=status_val,
        classification=classification,
        machine_id=machine_id,
        search=search
    )

    items = []
    for nc in records:
        total_rework = sum(r.rework_minutes for r in nc.rework_records)
        items.append(NCRecordResponse(
            id=nc.id,
            nc_number=nc.nc_number,
            quality_record_id=nc.quality_record_id,
            production_record_id=nc.production_record_id,
            machine_id=nc.machine_id,
            title=nc.title,
            description=nc.description,
            defect_category=nc.defect_category,
            classification=nc.classification,
            responsible_department=nc.responsible_department,
            quality_engineer_id=nc.quality_engineer_id,
            status=nc.status,
            root_cause=nc.root_cause,
            corrective_action=nc.corrective_action,
            preventive_action=nc.preventive_action,
            closed_at=nc.closed_at,
            closed_by_id=nc.closed_by_id,
            closure_notes=nc.closure_notes,
            created_at=nc.created_at,
            updated_at=nc.updated_at,
            machine_code=nc.machine.machine_code if nc.machine else None,
            machine_name=nc.machine.name if nc.machine else None,
            quality_engineer_name=nc.quality_engineer.full_name if nc.quality_engineer else None,
            closed_by_name=nc.closed_by.full_name if nc.closed_by else None,
            total_rework_minutes=total_rework
        ))

    return NCPaginationResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/nc/{nc_id}", response_model=NCRecordResponse, summary="Get NC details, RCA and rework history")
def get_nc_record(nc_id: int, db: Session = Depends(get_db)):
    nc = QualityService.get_nc_by_id(db, nc_id)
    total_rework = sum(r.rework_minutes for r in nc.rework_records)
    
    rework_items = [
        ReworkRecordResponse(
            id=r.id,
            nc_record_id=r.nc_record_id,
            production_record_id=r.production_record_id,
            machine_id=r.machine_id,
            rework_minutes=r.rework_minutes,
            rework_description=r.rework_description,
            rework_done_by_id=r.rework_done_by_id,
            verified_by_id=r.verified_by_id,
            completion_date=r.completion_date,
            rework_status=r.rework_status,
            notes=r.notes,
            created_at=r.created_at,
            updated_at=r.updated_at,
            rework_done_by_name=r.rework_done_by.full_name if r.rework_done_by else None,
            verified_by_name=r.verified_by.full_name if r.verified_by else None
        ) for r in nc.rework_records
    ]

    return NCRecordResponse(
        id=nc.id,
        nc_number=nc.nc_number,
        quality_record_id=nc.quality_record_id,
        production_record_id=nc.production_record_id,
        machine_id=nc.machine_id,
        title=nc.title,
        description=nc.description,
        defect_category=nc.defect_category,
        classification=nc.classification,
        responsible_department=nc.responsible_department,
        quality_engineer_id=nc.quality_engineer_id,
        status=nc.status,
        root_cause=nc.root_cause,
        corrective_action=nc.corrective_action,
        preventive_action=nc.preventive_action,
        closed_at=nc.closed_at,
        closed_by_id=nc.closed_by_id,
        closure_notes=nc.closure_notes,
        created_at=nc.created_at,
        updated_at=nc.updated_at,
        machine_code=nc.machine.machine_code if nc.machine else None,
        machine_name=nc.machine.name if nc.machine else None,
        quality_engineer_name=nc.quality_engineer.full_name if nc.quality_engineer else None,
        closed_by_name=nc.closed_by.full_name if nc.closed_by else None,
        total_rework_minutes=total_rework,
        rework_records=rework_items
    )


@router.put("/nc/{nc_id}", response_model=NCRecordResponse, summary="Update NC RCA and CAPA details")
async def update_nc(
    nc_id: int,
    nc_in: NCRecordUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    ip_addr = request.client.host if request.client else "127.0.0.1"
    updated = QualityService.update_nc_details(
        db=db,
        nc_id=nc_id,
        nc_in=nc_in,
        username="qe_priya",
        user_id=4,
        role="Quality Engineer",
        ip_address=ip_addr
    )
    return QualityService.get_nc_by_id(db, updated.id)


@router.patch("/nc/{nc_id}/status", response_model=NCRecordResponse, summary="Transition NC status in workflow")
async def transition_nc_status(
    nc_id: int,
    transition_req: NCStatusTransitionRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Enforces strict workflow progression:
    OPEN -> IN_PROGRESS -> UNDER_REVIEW -> CLOSED.
    Enforces role check: Only Quality Engineers & Administrators can close.
    """
    ip_addr = request.client.host if request.client else "127.0.0.1"
    updated = QualityService.transition_nc_status(
        db=db,
        nc_id=nc_id,
        req=transition_req,
        username="qe_priya" if transition_req.user_role == "Quality Engineer" else "admin",
        ip_address=ip_addr
    )

    # Broadcast WebSocket notification
    await ws_manager.broadcast("NC_STATUS_UPDATED", {
        "id": updated.id,
        "nc_number": updated.nc_number,
        "status": updated.status,
        "closed_by_id": updated.closed_by_id
    })

    return QualityService.get_nc_by_id(db, updated.id)


# -------------------------------------------------------------
# REWORK ENDPOINTS
# -------------------------------------------------------------
@router.post("/rework", response_model=ReworkRecordResponse, status_code=status.HTTP_201_CREATED, summary="Log rework activity")
async def create_rework_record(
    rework_in: ReworkRecordCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    ip_addr = request.client.host if request.client else "127.0.0.1"
    rework = QualityService.create_rework_record(
        db=db,
        rework_in=rework_in,
        username="operator_suresh",
        user_id=rework_in.rework_done_by_id,
        role="Operator",
        ip_address=ip_addr
    )

    await ws_manager.broadcast("REWORK_RECORD_CREATED", {
        "id": rework.id,
        "nc_record_id": rework.nc_record_id,
        "rework_minutes": rework.rework_minutes,
        "status": rework.rework_status
    })

    return ReworkRecordResponse(
        id=rework.id,
        nc_record_id=rework.nc_record_id,
        production_record_id=rework.production_record_id,
        machine_id=rework.machine_id,
        rework_minutes=rework.rework_minutes,
        rework_description=rework.rework_description,
        rework_done_by_id=rework.rework_done_by_id,
        verified_by_id=rework.verified_by_id,
        completion_date=rework.completion_date,
        rework_status=rework.rework_status,
        notes=rework.notes,
        created_at=rework.created_at,
        updated_at=rework.updated_at
    )


@router.patch("/rework/{rework_id}/status", response_model=ReworkRecordResponse, summary="Update rework status or sign-off verification")
async def update_rework_status(
    rework_id: int,
    status_in: ReworkStatusUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    ip_addr = request.client.host if request.client else "127.0.0.1"
    updated = QualityService.update_rework_status(
        db=db,
        rework_id=rework_id,
        req=status_in,
        username="qe_priya",
        user_id=status_in.verified_by_id or 4,
        role="Quality Engineer",
        ip_address=ip_addr
    )

    await ws_manager.broadcast("REWORK_RECORD_UPDATED", {
        "id": updated.id,
        "nc_record_id": updated.nc_record_id,
        "status": updated.rework_status
    })

    return ReworkRecordResponse(
        id=updated.id,
        nc_record_id=updated.nc_record_id,
        production_record_id=updated.production_record_id,
        machine_id=updated.machine_id,
        rework_minutes=updated.rework_minutes,
        rework_description=updated.rework_description,
        rework_done_by_id=updated.rework_done_by_id,
        verified_by_id=updated.verified_by_id,
        completion_date=updated.completion_date,
        rework_status=updated.rework_status,
        notes=updated.notes,
        created_at=updated.created_at,
        updated_at=updated.updated_at
    )

