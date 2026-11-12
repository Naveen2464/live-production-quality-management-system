import math
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_

from app.models.all_models import (
    QualityRecord, NCRecord, ReworkRecord, Machine, User, ProductionRecord,
    NCStatusEnum, ReworkStatusEnum
)
from app.schemas.quality import (
    QualityRecordCreate, NCRecordCreate, NCRecordUpdate,
    NCStatusTransitionRequest, ReworkRecordCreate, ReworkStatusUpdate
)
from app.services.audit_service import log_audit


class QualityService:

    @classmethod
    def generate_nc_number(cls, db: Session) -> str:
        """Generates a sequential human-readable NC tracking identifier: NC-YYYY-0001."""
        current_year = datetime.now(timezone.utc).year
        prefix = f"NC-{current_year}-"
        
        # Count existing NCs for this year
        count = db.query(func.count(NCRecord.id)).filter(
            NCRecord.nc_number.like(f"{prefix}%")
        ).scalar() or 0
        
        return f"{prefix}{str(count + 1).zfill(4)}"

    # -------------------------------------------------------------
    # QUALITY RECORDS
    # -------------------------------------------------------------
    @classmethod
    def create_quality_record(
        cls,
        db: Session,
        record_in: QualityRecordCreate,
        username: str,
        user_id: int,
        role: str = "Quality Engineer",
        ip_address: Optional[str] = None
    ) -> Tuple[QualityRecord, Optional[NCRecord]]:
        # Verify machine exists
        machine = db.query(Machine).filter(Machine.id == record_in.machine_id).first()
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine #{record_in.machine_id} not found."
            )

        # Check production record link
        prod_rec = None
        if record_in.production_record_id:
            prod_rec = db.query(ProductionRecord).filter(
                ProductionRecord.id == record_in.production_record_id
            ).first()
            if prod_rec:
                # Synchronize NC Raised flag on production run
                prod_rec.nc_raised = True
                if record_in.rework_minutes > 0:
                    prod_rec.rework_time += record_in.rework_minutes

        # Create Quality Record
        q_record = QualityRecord(
            production_record_id=record_in.production_record_id,
            machine_id=record_in.machine_id,
            defect_description=record_in.defect_description,
            defect_category=record_in.defect_category,
            date_of_occurrence=record_in.date_of_occurrence,
            responsible_department=record_in.responsible_department,
            severity=record_in.severity.upper(),
            rework_minutes=record_in.rework_minutes,
            created_by_id=user_id
        )
        db.add(q_record)
        db.commit()
        db.refresh(q_record)

        # Audit Quality Record
        log_audit(
            db=db,
            action="CREATE",
            module="QUALITY",
            record_id=str(q_record.id),
            username=username,
            user_id=user_id,
            role=role,
            new_values={
                "id": q_record.id,
                "machine_id": q_record.machine_id,
                "defect_category": q_record.defect_category,
                "severity": q_record.severity,
                "production_record_id": q_record.production_record_id
            },
            ip_address=ip_address
        )

        # Optional Auto-Spawn NC Record
        nc_record = None
        if record_in.create_nc:
            nc_number = cls.generate_nc_number(db)
            nc_record = NCRecord(
                nc_number=nc_number,
                quality_record_id=q_record.id,
                production_record_id=q_record.production_record_id,
                machine_id=q_record.machine_id,
                title=f"Defect on {machine.machine_code}: {record_in.defect_category}",
                description=record_in.defect_description,
                defect_category=record_in.defect_category,
                classification=record_in.nc_classification or "MAJOR",
                responsible_department=record_in.responsible_department,
                quality_engineer_id=user_id,
                status=NCStatusEnum.OPEN.value
            )
            db.add(nc_record)
            db.commit()
            db.refresh(nc_record)

            # Audit NC Record
            log_audit(
                db=db,
                action="CREATE",
                module="NC",
                record_id=str(nc_record.id),
                username=username,
                user_id=user_id,
                role=role,
                new_values={
                    "nc_number": nc_record.nc_number,
                    "status": nc_record.status,
                    "classification": nc_record.classification,
                    "machine_id": nc_record.machine_id
                },
                ip_address=ip_address
            )

        return q_record, nc_record

    @classmethod
    def get_quality_records(
        cls,
        db: Session,
        page: int = 1,
        page_size: int = 10,
        machine_id: Optional[int] = None,
        defect_category: Optional[str] = None,
        severity: Optional[str] = None
    ) -> Tuple[List[QualityRecord], int, int]:
        query = db.query(QualityRecord).options(
            joinedload(QualityRecord.machine),
            joinedload(QualityRecord.created_by),
            joinedload(QualityRecord.nc_record)
        )
        if machine_id:
            query = query.filter(QualityRecord.machine_id == machine_id)
        if defect_category:
            query = query.filter(QualityRecord.defect_category == defect_category)
        if severity:
            query = query.filter(QualityRecord.severity == severity.upper())

        total = query.count()
        pages = math.ceil(total / page_size) if total > 0 else 1
        records = query.order_by(desc(QualityRecord.id)).offset((page - 1) * page_size).limit(page_size).all()
        return records, total, pages

    # -------------------------------------------------------------
    # NON-CONFORMANCE (NC) WORKFLOW
    # -------------------------------------------------------------
    @classmethod
    def create_nc_record(
        cls,
        db: Session,
        nc_in: NCRecordCreate,
        username: str,
        user_id: int,
        role: str = "Quality Engineer",
        ip_address: Optional[str] = None
    ) -> NCRecord:
        nc_number = cls.generate_nc_number(db)
        nc = NCRecord(
            nc_number=nc_number,
            quality_record_id=nc_in.quality_record_id,
            production_record_id=nc_in.production_record_id,
            machine_id=nc_in.machine_id,
            title=nc_in.title,
            description=nc_in.description,
            defect_category=nc_in.defect_category,
            classification=nc_in.classification.upper(),
            responsible_department=nc_in.responsible_department,
            quality_engineer_id=nc_in.quality_engineer_id or user_id,
            status=NCStatusEnum.OPEN.value
        )
        db.add(nc)
        db.commit()
        db.refresh(nc)

        log_audit(
            db=db,
            action="CREATE",
            module="NC",
            record_id=str(nc.id),
            username=username,
            user_id=user_id,
            role=role,
            new_values={
                "nc_number": nc.nc_number,
                "title": nc.title,
                "classification": nc.classification,
                "status": nc.status
            },
            ip_address=ip_address
        )
        return nc

    @classmethod
    def get_ncs(
        cls,
        db: Session,
        page: int = 1,
        page_size: int = 10,
        status_val: Optional[str] = None,
        classification: Optional[str] = None,
        machine_id: Optional[int] = None,
        search: Optional[str] = None
    ) -> Tuple[List[NCRecord], int, int]:
        query = db.query(NCRecord).options(
            joinedload(NCRecord.machine),
            joinedload(NCRecord.quality_engineer),
            joinedload(NCRecord.closed_by),
            joinedload(NCRecord.rework_records)
        )
        if status_val:
            query = query.filter(NCRecord.status == status_val.upper())
        if classification:
            query = query.filter(NCRecord.classification == classification.upper())
        if machine_id:
            query = query.filter(NCRecord.machine_id == machine_id)
        if search:
            s = f"%{search}%"
            query = query.filter(
                or_(
                    NCRecord.nc_number.ilike(s),
                    NCRecord.title.ilike(s),
                    NCRecord.description.ilike(s)
                )
            )

        total = query.count()
        pages = math.ceil(total / page_size) if total > 0 else 1
        items = query.order_by(desc(NCRecord.id)).offset((page - 1) * page_size).limit(page_size).all()
        return items, total, pages

    @classmethod
    def get_nc_by_id(cls, db: Session, nc_id: int) -> NCRecord:
        nc = db.query(NCRecord).options(
            joinedload(NCRecord.machine),
            joinedload(NCRecord.quality_engineer),
            joinedload(NCRecord.closed_by),
            joinedload(NCRecord.rework_records)
        ).filter(NCRecord.id == nc_id).first()
        if not nc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"NC record #{nc_id} not found."
            )
        return nc

    @classmethod
    def update_nc_details(
        cls,
        db: Session,
        nc_id: int,
        nc_in: NCRecordUpdate,
        username: str,
        user_id: int,
        role: str,
        ip_address: Optional[str] = None
    ) -> NCRecord:
        nc = cls.get_nc_by_id(db, nc_id)
        if nc.status == NCStatusEnum.CLOSED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a closed NC case without reopening by an Administrator."
            )

        prev_values = {
            "title": nc.title,
            "root_cause": nc.root_cause,
            "corrective_action": nc.corrective_action,
            "preventive_action": nc.preventive_action
        }

        update_data = nc_in.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(nc, key, val)
        nc.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(nc)

        log_audit(
            db=db,
            action="UPDATE_RCA",
            module="NC",
            record_id=str(nc.id),
            username=username,
            user_id=user_id,
            role=role,
            previous_values=prev_values,
            new_values={
                "title": nc.title,
                "root_cause": nc.root_cause,
                "corrective_action": nc.corrective_action,
                "preventive_action": nc.preventive_action
            },
            ip_address=ip_address
        )
        return nc

    @classmethod
    def transition_nc_status(
        cls,
        db: Session,
        nc_id: int,
        req: NCStatusTransitionRequest,
        username: str,
        ip_address: Optional[str] = None
    ) -> NCRecord:
        """
        Enforces strict NC status workflow:
        OPEN -> IN_PROGRESS -> UNDER_REVIEW -> CLOSED.
        Also allows UNDER_REVIEW -> IN_PROGRESS.
        Enforces role authorization (only QE and Admin can close).
        """
        nc = cls.get_nc_by_id(db, nc_id)
        curr_status = nc.status
        target_status = req.target_status.upper()

        if curr_status == target_status:
            return nc  # No state change

        # Workflow state transition rules
        valid_transitions = {
            NCStatusEnum.OPEN.value: [NCStatusEnum.IN_PROGRESS.value],
            NCStatusEnum.IN_PROGRESS.value: [NCStatusEnum.UNDER_REVIEW.value],
            NCStatusEnum.UNDER_REVIEW.value: [NCStatusEnum.CLOSED.value, NCStatusEnum.IN_PROGRESS.value],
            NCStatusEnum.CLOSED.value: [] # Closed is terminal unless admin override
        }

        allowed_next = valid_transitions.get(curr_status, [])
        if target_status not in allowed_next:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Workflow Transition: Cannot move NC from '{curr_status}' directly to '{target_status}'. Permitted next steps from {curr_status}: {allowed_next}"
            )

        # Role enforcement for CLOSURE
        if target_status == NCStatusEnum.CLOSED.value:
            if req.user_role not in ["Quality Engineer", "Administrator"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission Denied: User role '{req.user_role}' is not authorized to close NC cases. Quality Engineer or Administrator role required."
                )
            if not req.closure_notes or len(req.closure_notes.strip()) < 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Closure verification notes (at least 5 characters) are mandatory to formally close an NC case."
                )
            nc.closed_at = datetime.now(timezone.utc)
            nc.closed_by_id = req.user_id
            nc.closure_notes = req.closure_notes.strip()

        # Update root cause / corrective action if provided during transition
        if req.root_cause:
            nc.root_cause = req.root_cause
        if req.corrective_action:
            nc.corrective_action = req.corrective_action

        nc.status = target_status
        nc.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(nc)

        log_audit(
            db=db,
            action="CLOSE" if target_status == NCStatusEnum.CLOSED.value else "STATUS_CHANGE",
            module="NC",
            record_id=str(nc.id),
            username=username,
            user_id=req.user_id,
            role=req.user_role,
            previous_values={"status": curr_status},
            new_values={
                "status": target_status,
                "closure_notes": nc.closure_notes,
                "closed_by_id": nc.closed_by_id
            },
            ip_address=ip_address
        )
        return nc

    # -------------------------------------------------------------
    # REWORK TRACKING
    # -------------------------------------------------------------
    @classmethod
    def create_rework_record(
        cls,
        db: Session,
        rework_in: ReworkRecordCreate,
        username: str,
        user_id: int,
        role: str = "Quality Engineer",
        ip_address: Optional[str] = None
    ) -> ReworkRecord:
        nc = cls.get_nc_by_id(db, rework_in.nc_record_id)

        rework = ReworkRecord(
            nc_record_id=rework_in.nc_record_id,
            production_record_id=rework_in.production_record_id or nc.production_record_id,
            machine_id=rework_in.machine_id or nc.machine_id,
            rework_minutes=rework_in.rework_minutes,
            rework_description=rework_in.rework_description,
            rework_done_by_id=rework_in.rework_done_by_id,
            verified_by_id=rework_in.verified_by_id,
            completion_date=rework_in.completion_date,
            rework_status=rework_in.rework_status.upper(),
            notes=rework_in.notes
        )
        db.add(rework)

        # Synchronize rework minutes with linked production record if present
        if rework.production_record_id:
            prod = db.query(ProductionRecord).filter(
                ProductionRecord.id == rework.production_record_id
            ).first()
            if prod:
                prod.rework_time = round(float(prod.rework_time or 0.0) + float(rework.rework_minutes), 2)

        db.commit()
        db.refresh(rework)

        log_audit(
            db=db,
            action="CREATE",
            module="REWORK",
            record_id=str(rework.id),
            username=username,
            user_id=user_id,
            role=role,
            new_values={
                "nc_record_id": rework.nc_record_id,
                "rework_minutes": rework.rework_minutes,
                "rework_status": rework.rework_status
            },
            ip_address=ip_address
        )
        return rework

    @classmethod
    def update_rework_status(
        cls,
        db: Session,
        rework_id: int,
        req: ReworkStatusUpdate,
        username: str,
        user_id: int,
        role: str,
        ip_address: Optional[str] = None
    ) -> ReworkRecord:
        rework = db.query(ReworkRecord).filter(ReworkRecord.id == rework_id).first()
        if not rework:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rework record #{rework_id} not found."
            )

        prev_status = rework.rework_status
        rework.rework_status = req.rework_status.upper()
        if req.verified_by_id:
            rework.verified_by_id = req.verified_by_id
        if req.completion_date:
            rework.completion_date = req.completion_date
        if req.notes:
            rework.notes = req.notes
        rework.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(rework)

        log_audit(
            db=db,
            action="VERIFY" if rework.rework_status == "VERIFIED" else "UPDATE",
            module="REWORK",
            record_id=str(rework.id),
            username=username,
            user_id=user_id,
            role=role,
            previous_values={"rework_status": prev_status},
            new_values={"rework_status": rework.rework_status},
            ip_address=ip_address
        )
        return rework

