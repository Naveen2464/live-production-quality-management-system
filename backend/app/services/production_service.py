import math
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc

from app.models.all_models import (
    ProductionRecord, Machine, Frame, Shift, User, Customer,
    ApprovalStatusEnum, NCRecord, QualityRecord
)
from app.schemas.production import (
    ProductionRecordCreate, ProductionRecordUpdate, ProductionApprovalRequest
)
from app.services.audit_service import log_audit


class ProductionService:
    @staticmethod
    def calculate_cycle_times(static: float, mounting: float, rotational: float, dismantling: float) -> Tuple[float, float]:
        """Calculates total testing time (minutes) and cycle time (hours)."""
        total = round(float(static) + float(mounting) + float(rotational) + float(dismantling), 2)
        hours = round(total / 60.0, 4)
        return total, hours

    @classmethod
    def check_duplicate(cls, db: Session, machine_id: int, date_val: Any, shift_id: int, exclude_id: Optional[int] = None) -> None:
        """
        Enforces business rule: No duplicate active record for the same machine,
        date, and shift unless the previous record was REJECTED.
        """
        query = db.query(ProductionRecord).filter(
            ProductionRecord.machine_id == machine_id,
            ProductionRecord.date == date_val,
            ProductionRecord.shift_id == shift_id,
            ProductionRecord.approval_status != ApprovalStatusEnum.REJECTED.value
        )
        if exclude_id:
            query = query.filter(ProductionRecord.id != exclude_id)
        
        existing = query.first()
        if existing:
            machine = db.query(Machine).filter(Machine.id == machine_id).first()
            shift = db.query(Shift).filter(Shift.id == shift_id).first()
            machine_name = machine.machine_code if machine else str(machine_id)
            shift_name = shift.shift_name if shift else str(shift_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate Record: Machine '{machine_name}' has an active production record on {date_val} for {shift_name} (Record ID #{existing.id})."
            )

    @classmethod
    def create_record(
        cls,
        db: Session,
        record_in: ProductionRecordCreate,
        username: str = "operator",
        user_id: Optional[int] = None,
        role: Optional[str] = "Operator",
        ip_address: Optional[str] = None
    ) -> ProductionRecord:
        # 1. Enforce Duplicate Prevention
        cls.check_duplicate(db, record_in.machine_id, record_in.date, record_in.shift_id)

        # 2. Strict Backend Time Calculation
        total_time, cycle_hours = cls.calculate_cycle_times(
            record_in.static_time,
            record_in.mounting_time,
            record_in.rotational_time,
            record_in.dismantling_time
        )

        # 3. Create ORM instance
        record = ProductionRecord(
            date=record_in.date,
            machine_id=record_in.machine_id,
            frame_id=record_in.frame_id,
            shift_id=record_in.shift_id,
            operator_id=record_in.operator_id,
            supervisor_id=record_in.supervisor_id,
            customer_id=record_in.customer_id,
            static_time=record_in.static_time,
            mounting_time=record_in.mounting_time,
            rotational_time=record_in.rotational_time,
            dismantling_time=record_in.dismantling_time,
            total_testing_time=total_time,
            cycle_time_hours=cycle_hours,
            test_result=record_in.test_result.upper(),
            nc_raised=record_in.nc_raised,
            rework_time=record_in.rework_time,
            approval_status=ApprovalStatusEnum.PENDING.value,
            notes=record_in.notes
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        # 4. Audit Log
        log_audit(
            db=db,
            action="CREATE",
            module="PRODUCTION",
            record_id=str(record.id),
            username=username,
            user_id=user_id or record_in.operator_id,
            role=role,
            new_values={
                "id": record.id,
                "date": str(record.date),
                "machine_id": record.machine_id,
                "total_testing_time": record.total_testing_time,
                "cycle_time_hours": record.cycle_time_hours,
                "test_result": record.test_result,
                "approval_status": record.approval_status
            },
            ip_address=ip_address
        )

        return record

    @classmethod
    def get_records(
        cls,
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        machine_id: Optional[int] = None,
        shift_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        approval_status: Optional[str] = None
    ) -> Tuple[List[ProductionRecord], int, int]:
        query = db.query(ProductionRecord).options(
            joinedload(ProductionRecord.machine),
            joinedload(ProductionRecord.frame),
            joinedload(ProductionRecord.shift),
            joinedload(ProductionRecord.operator),
            joinedload(ProductionRecord.supervisor),
            joinedload(ProductionRecord.customer)
        )

        # Filters
        if machine_id:
            query = query.filter(ProductionRecord.machine_id == machine_id)
        if shift_id:
            query = query.filter(ProductionRecord.shift_id == shift_id)
        if customer_id:
            query = query.filter(ProductionRecord.customer_id == customer_id)
        if approval_status:
            query = query.filter(ProductionRecord.approval_status == approval_status.upper())
        if start_date:
            query = query.filter(ProductionRecord.date >= start_date)
        if end_date:
            query = query.filter(ProductionRecord.date <= end_date)
        
        # Free-text search on Machine code or Customer name
        if search:
            search_pattern = f"%{search}%"
            query = query.join(ProductionRecord.machine).join(ProductionRecord.customer).filter(
                or_(
                    Machine.machine_code.ilike(search_pattern),
                    Machine.name.ilike(search_pattern),
                    Customer.customer_name.ilike(search_pattern),
                    Customer.customer_code.ilike(search_pattern)
                )
            )

        total_count = query.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        offset = (page - 1) * page_size
        records = query.order_by(
            desc(ProductionRecord.date),
            desc(ProductionRecord.id)
        ).offset(offset).limit(page_size).all()

        return records, total_count, total_pages

    @classmethod
    def get_record_by_id(cls, db: Session, record_id: int) -> ProductionRecord:
        record = db.query(ProductionRecord).options(
            joinedload(ProductionRecord.machine),
            joinedload(ProductionRecord.frame),
            joinedload(ProductionRecord.shift),
            joinedload(ProductionRecord.operator),
            joinedload(ProductionRecord.supervisor),
            joinedload(ProductionRecord.customer)
        ).filter(ProductionRecord.id == record_id).first()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Production record #{record_id} not found."
            )
        return record

    @classmethod
    def update_record(
        cls,
        db: Session,
        record_id: int,
        update_in: ProductionRecordUpdate,
        username: str = "supervisor",
        user_id: Optional[int] = None,
        role: Optional[str] = "Supervisor",
        ip_address: Optional[str] = None
    ) -> ProductionRecord:
        record = cls.get_record_by_id(db, record_id)

        # Enforce approval lock: Approved records require supervisor/admin override
        if record.approval_status == ApprovalStatusEnum.APPROVED.value and role not in ["Supervisor", "Administrator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Approved records cannot be modified without Supervisor or Administrator authorization."
            )

        # Check duplicate if machine, date, or shift changed
        new_machine = update_in.machine_id or record.machine_id
        new_date = update_in.date or record.date
        new_shift = update_in.shift_id or record.shift_id
        if (new_machine != record.machine_id or new_date != record.date or new_shift != record.shift_id):
            cls.check_duplicate(db, new_machine, new_date, new_shift, exclude_id=record.id)

        prev_values = {
            "static_time": record.static_time,
            "mounting_time": record.mounting_time,
            "rotational_time": record.rotational_time,
            "dismantling_time": record.dismantling_time,
            "total_testing_time": record.total_testing_time,
            "cycle_time_hours": record.cycle_time_hours,
            "test_result": record.test_result,
            "nc_raised": record.nc_raised,
            "rework_time": record.rework_time
        }

        # Apply updates
        update_data = update_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)

        # Recalculate timing if any stage time was updated
        total_time, cycle_hours = cls.calculate_cycle_times(
            record.static_time,
            record.mounting_time,
            record.rotational_time,
            record.dismantling_time
        )
        record.total_testing_time = total_time
        record.cycle_time_hours = cycle_hours
        record.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(record)

        # Audit
        log_audit(
            db=db,
            action="UPDATE",
            module="PRODUCTION",
            record_id=str(record.id),
            username=username,
            user_id=user_id,
            role=role,
            previous_values=prev_values,
            new_values={
                "total_testing_time": record.total_testing_time,
                "cycle_time_hours": record.cycle_time_hours,
                "test_result": record.test_result,
                "nc_raised": record.nc_raised,
                "rework_time": record.rework_time
            },
            ip_address=ip_address
        )

        return record

    @classmethod
    def approve_or_reject(
        cls,
        db: Session,
        record_id: int,
        approval_in: ProductionApprovalRequest,
        username: str = "supervisor",
        role: str = "Supervisor",
        ip_address: Optional[str] = None
    ) -> ProductionRecord:
        record = cls.get_record_by_id(db, record_id)

        action = approval_in.action.upper()
        if action not in ["APPROVE", "REJECT"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid approval action. Must be 'APPROVE' or 'REJECT'."
            )

        prev_status = record.approval_status
        if action == "APPROVE":
            record.approval_status = ApprovalStatusEnum.APPROVED.value
            record.rejection_reason = None
        else:
            record.approval_status = ApprovalStatusEnum.REJECTED.value
            record.rejection_reason = approval_in.rejection_reason

        record.approved_by_id = approval_in.supervisor_id
        record.approved_at = datetime.now(timezone.utc)
        record.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(record)

        # Audit Log
        log_audit(
            db=db,
            action=action,
            module="PRODUCTION",
            record_id=str(record.id),
            username=username,
            user_id=approval_in.supervisor_id,
            role=role,
            previous_values={"approval_status": prev_status},
            new_values={
                "approval_status": record.approval_status,
                "approved_by_id": record.approved_by_id,
                "rejection_reason": record.rejection_reason
            },
            ip_address=ip_address
        )

        return record
