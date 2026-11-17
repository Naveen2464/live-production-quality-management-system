import io
import uuid
import math
import logging
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.all_models import (
    ProductionRecord, QualityRecord, NCRecord, Machine, Frame, Shift,
    Customer, User, ImportHistory, ImportError, ApprovalStatusEnum, NCStatusEnum
)
from app.schemas.migration import (
    ImportValidateResponse, ImportErrorItem, ImportConfirmResponse
)
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)

# Temporary in-memory cache for validated batches awaiting user confirmation
# batch_id -> { "file_name": str, "file_type": str, "valid_records": List[dict], "errors": List[dict], "total_rows": int, "duplicate_count": int }
BATCH_CACHE: Dict[str, Dict[str, Any]] = {}


class MigrationService:

    @staticmethod
    def _normalize_date(val: Any) -> Optional[date]:
        """Safely parses various date formats from Excel (timestamps, ISO strings, etc.)."""
        if pd.isna(val) or val is None or str(val).strip() == "":
            return None
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.date()
        if isinstance(val, date):
            return val
        str_val = str(val).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(str_val, fmt).date()
            except ValueError:
                continue
        # Fallback pandas parse
        try:
            parsed = pd.to_datetime(str_val, errors="coerce")
            if not pd.isna(parsed):
                return parsed.date()
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_float(val: Any, default: float = 0.0) -> float:
        if pd.isna(val) or val is None or str(val).strip() == "":
            return default
        try:
            num = float(val)
            return round(num, 2) if not math.isnan(num) else default
        except (ValueError, TypeError):
            return -1.0  # Sentinel for invalid float

    @staticmethod
    def _parse_bool(val: Any) -> bool:
        if pd.isna(val) or val is None:
            return False
        s = str(val).strip().lower()
        return s in ("yes", "true", "1", "y", "t")

    @classmethod
    def validate_excel_file(
        cls,
        db: Session,
        file_bytes: bytes,
        file_name: str,
        file_type: str = "PRODUCTION"
    ) -> ImportValidateResponse:
        """
        Parses and validates Excel spreadsheets using Pandas.
        Detects columns, verifies dates and machine numbers, checks for duplicates,
        and generates a validation preview with rejected rows breakdown.
        """
        # Read Excel safely without macro execution (data_only=True via openpyxl)
        try:
            excel_file = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
            sheet_name = excel_file.sheet_names[0]
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, engine="openpyxl")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or corrupted Excel file: {str(e)}"
            )

        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded Excel sheet contains no data rows."
            )

        # Standardize column headers (strip spaces, lowercase)
        raw_cols = [str(c).strip() for c in df.columns]
        norm_map = {str(c).strip().lower().replace(" ", "_"): c for c in raw_cols}

        # Master Lookups Cache
        machines_cache = {m.machine_code.upper(): m for m in db.query(Machine).all()}
        # Also allow matching by machine ID or Name
        frames_cache = {f.frame_code.upper(): f for f in db.query(Frame).all()}
        shifts_cache = {s.shift_name.upper(): s for s in db.query(Shift).all()}
        customers_cache = {c.customer_code.upper(): c for c in db.query(Customer).all()}
        for c in db.query(Customer).all():
            customers_cache[c.customer_name.upper()] = c
        users_cache = {u.username.upper(): u for u in db.query(User).all()}
        for u in db.query(User).all():
            users_cache[u.full_name.upper()] = u

        default_operator = db.query(User).filter(User.role_id == 5).first() or db.query(User).first()
        default_supervisor = db.query(User).filter(User.role_id == 2).first() or db.query(User).first()
        default_frame = db.query(Frame).first()
        default_shift = db.query(Shift).first()
        default_customer = db.query(Customer).first()

        valid_records: List[Dict[str, Any]] = []
        errors: List[ImportErrorItem] = []
        duplicates_count = 0
        seen_in_sheet = set()

        if file_type.upper() == "PRODUCTION":
            for idx, row in df.iterrows():
                row_num = idx + 2  # Excel 1-based index + header row
                raw_row = {str(k): (None if pd.isna(v) else str(v)) for k, v in row.items()}

                # Extract and map columns
                date_raw = row.get("Date") or row.get("Testing Date") or row.get("Test Date") or row.get("date")
                parsed_date = cls._normalize_date(date_raw)
                if not parsed_date:
                    errors.append(ImportErrorItem(
                        row_number=row_num,
                        error_type="INVALID_DATE",
                        field_name="Date",
                        error_message=f"Date '{date_raw}' is missing, invalid or corrupt.",
                        raw_data=raw_row
                    ))
                    continue

                # Machine code
                mach_raw = str(row.get("Machine Number") or row.get("Machine Code") or row.get("Machine") or row.get("machine_code") or "").strip()
                if not mach_raw:
                    errors.append(ImportErrorItem(
                        row_number=row_num,
                        error_type="MISSING_MACHINE",
                        field_name="Machine Number",
                        error_message="Machine Number is mandatory but was left empty.",
                        raw_data=raw_row
                    ))
                    continue

                matched_machine = machines_cache.get(mach_raw.upper())
                if not matched_machine:
                    # Try partial match (e.g. "M-101" inside "Test Bed 01")
                    for k, m_obj in machines_cache.items():
                        if k in mach_raw.upper() or mach_raw.upper() in m_obj.name.upper():
                            matched_machine = m_obj
                            break

                if not matched_machine:
                    errors.append(ImportErrorItem(
                        row_number=row_num,
                        error_type="UNKNOWN_MACHINE",
                        field_name="Machine Number",
                        error_message=f"Machine '{mach_raw}' is not registered in the system master database.",
                        raw_data=raw_row
                    ))
                    continue

                # Shift
                shift_raw = str(row.get("Shift") or row.get("Work Shift") or "Shift A").strip()
                matched_shift = shifts_cache.get(shift_raw.upper()) or default_shift

                # Duplicate Check: Within the uploaded spreadsheet
                sheet_key = (matched_machine.id, parsed_date, matched_shift.id)
                if sheet_key in seen_in_sheet:
                    duplicates_count += 1
                    errors.append(ImportErrorItem(
                        row_number=row_num,
                        error_type="DUPLICATE_IN_FILE",
                        field_name="Machine Number",
                        error_message=f"Duplicate test run in same spreadsheet for {matched_machine.machine_code} on {parsed_date} ({matched_shift.shift_name}).",
                        raw_data=raw_row
                    ))
                    continue
                seen_in_sheet.add(sheet_key)

                # Duplicate Check: Against existing database records
                db_dup = db.query(ProductionRecord).filter(
                    ProductionRecord.machine_id == matched_machine.id,
                    ProductionRecord.date == parsed_date,
                    ProductionRecord.shift_id == matched_shift.id,
                    ProductionRecord.approval_status != ApprovalStatusEnum.REJECTED.value
                ).first()

                if db_dup:
                    duplicates_count += 1
                    errors.append(ImportErrorItem(
                        row_number=row_num,
                        error_type="DUPLICATE_IN_DATABASE",
                        field_name="Machine Number",
                        error_message=f"Record already exists in database for {matched_machine.machine_code} on {parsed_date} ({matched_shift.shift_name}, ID #{db_dup.id}).",
                        raw_data=raw_row
                    ))
                    continue

                # Frame
                frame_raw = str(row.get("Frame") or row.get("Frame Size") or "").strip()
                matched_frame = frames_cache.get(frame_raw.upper()) or default_frame

                # Customer
                cust_raw = str(row.get("Customer") or row.get("Client") or "").strip()
                matched_cust = customers_cache.get(cust_raw.upper()) or default_customer

                # Operator & Supervisor
                op_raw = str(row.get("Operator") or "").strip()
                matched_op = users_cache.get(op_raw.upper()) or default_operator

                sup_raw = str(row.get("Supervisor") or "").strip()
                matched_sup = users_cache.get(sup_raw.upper()) or default_supervisor

                # Timings
                static_t = cls._parse_float(row.get("Static Testing Time") or row.get("Static Time") or row.get("static_time"))
                mount_t = cls._parse_float(row.get("Mounting Time") or row.get("mounting_time"))
                rot_t = cls._parse_float(row.get("Rotational Testing Time") or row.get("Rotational Time") or row.get("rotational_time"))
                dism_t = cls._parse_float(row.get("Dismantling Time") or row.get("dismantling_time"))

                if any(t < 0 for t in (static_t, mount_t, rot_t, dism_t)):
                    errors.append(ImportErrorItem(
                        row_number=row_num,
                        error_type="INVALID_NUMERIC",
                        field_name="Timing Fields",
                        error_message="Stage testing times must be valid non-negative numbers.",
                        raw_data=raw_row
                    ))
                    continue

                total_calc = round(static_t + mount_t + rot_t + dism_t, 2)
                cycle_calc = round(total_calc / 60.0, 4)

                test_res = str(row.get("Test Result") or row.get("Result") or "PASS").strip().upper()
                if test_res not in ("PASS", "FAIL", "CONDITIONAL"):
                    test_res = "PASS"

                nc_raised = cls._parse_bool(row.get("NC Raised") or row.get("NC Raised (Yes/No)"))
                rework_t = max(0.0, cls._parse_float(row.get("Rework Time") or row.get("rework_time"), default=0.0))
                notes_val = str(row.get("Notes") or row.get("Remarks") or "").strip() or None

                valid_records.append({
                    "date": parsed_date,
                    "machine_id": matched_machine.id,
                    "machine_code": matched_machine.machine_code,
                    "frame_id": matched_frame.id,
                    "shift_id": matched_shift.id,
                    "customer_id": matched_cust.id,
                    "operator_id": matched_op.id,
                    "supervisor_id": matched_sup.id,
                    "static_time": static_t,
                    "mounting_time": mount_t,
                    "rotational_time": rot_t,
                    "dismantling_time": dism_t,
                    "total_testing_time": total_calc,
                    "cycle_time_hours": cycle_calc,
                    "test_result": test_res,
                    "nc_raised": nc_raised,
                    "rework_time": rework_t,
                    "notes": notes_val
                })

        else:
            # QUALITY / NC WORKBOOK
            for idx, row in df.iterrows():
                row_num = idx + 2
                raw_row = {str(k): (None if pd.isna(v) else str(v)) for k, v in row.items()}

                date_raw = row.get("Date") or row.get("Occurrence Date") or row.get("Date of Occurrence")
                parsed_date = cls._normalize_date(date_raw) or date.today()

                mach_raw = str(row.get("Machine Number") or row.get("Machine Code") or row.get("Machine") or "").strip()
                matched_machine = machines_cache.get(mach_raw.upper())
                if not matched_machine and mach_raw:
                    for k, m_obj in machines_cache.items():
                        if k in mach_raw.upper() or mach_raw.upper() in m_obj.name.upper():
                            matched_machine = m_obj
                            break
                if not matched_machine:
                    matched_machine = db.query(Machine).first()

                desc_val = str(row.get("Defect Description") or row.get("Description") or row.get("Issue") or "").strip()
                if not desc_val or len(desc_val) < 3:
                    errors.append(ImportErrorItem(
                        row_number=row_num,
                        error_type="MISSING_DESCRIPTION",
                        field_name="Defect Description",
                        error_message="Defect description cannot be blank.",
                        raw_data=raw_row
                    ))
                    continue

                cat_val = str(row.get("Defect Category") or row.get("Category") or "Mechanical").strip()
                dept_val = str(row.get("Responsible Department") or row.get("Department") or "Quality Assurance").strip()
                sev_val = str(row.get("Severity") or "MEDIUM").strip().upper()
                if sev_val not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
                    sev_val = "MEDIUM"

                class_val = str(row.get("Classification") or "MAJOR").strip().upper()
                if class_val not in ("MINOR", "MAJOR", "CRITICAL"):
                    class_val = "MAJOR"

                status_val = str(row.get("Status") or row.get("NC Status") or "OPEN").strip().upper()
                if status_val not in ("OPEN", "IN_PROGRESS", "UNDER_REVIEW", "CLOSED"):
                    status_val = "OPEN"

                rework_mins = max(0.0, cls._parse_float(row.get("Rework Minutes") or row.get("Rework Time"), default=0.0))
                root_cause = str(row.get("Root Cause") or row.get("RCA") or "").strip() or None
                corrective = str(row.get("Corrective Action") or row.get("CAPA") or "").strip() or None

                valid_records.append({
                    "date_of_occurrence": parsed_date,
                    "machine_id": matched_machine.id,
                    "machine_code": matched_machine.machine_code,
                    "defect_description": desc_val,
                    "defect_category": cat_val,
                    "responsible_department": dept_val,
                    "severity": sev_val,
                    "rework_minutes": rework_mins,
                    "classification": class_val,
                    "status": status_val,
                    "root_cause": root_cause,
                    "corrective_action": corrective
                })

        # Save to temporary batch cache
        batch_id = str(uuid.uuid4())
        BATCH_CACHE[batch_id] = {
            "file_name": file_name,
            "file_type": file_type.upper(),
            "valid_records": valid_records,
            "errors": [e.model_dump() for e in errors],
            "total_rows": len(df),
            "duplicate_count": duplicates_count
        }

        # Preview sample (up to 10 rows)
        sample = []
        for r in valid_records[:10]:
            sample.append({k: (str(v) if isinstance(v, date) else v) for k, v in r.items()})

        return ImportValidateResponse(
            batch_id=batch_id,
            file_name=file_name,
            file_type=file_type.upper(),
            detected_sheet=sheet_name,
            detected_columns=raw_cols,
            mapped_columns=norm_map,
            total_rows=len(df),
            valid_count=len(valid_records),
            rejected_count=len(errors),
            duplicate_count=duplicates_count,
            sample_valid_rows=sample,
            rejected_rows=errors,
            can_commit=len(valid_records) > 0
        )

    @classmethod
    def confirm_import(
        cls,
        db: Session,
        batch_id: str,
        user_id: int,
        username: str,
        role: str,
        ip_address: Optional[str] = None
    ) -> ImportConfirmResponse:
        """
        Executes database insertion of validated batch inside a strict atomic transaction.
        Writes to ImportHistory, ImportError, and AuditLog tables.
        """
        batch = BATCH_CACHE.get(batch_id)
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Batch ID not found or expired. Please upload and validate the file again."
            )

        valid_records = batch["valid_records"]
        errors = batch["errors"]
        file_name = batch["file_name"]
        file_type = batch["file_type"]

        if not valid_records:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid records available in this batch to import."
            )

        try:
            # 1. Create Import History Header
            history = ImportHistory(
                file_name=file_name,
                file_type=file_type,
                total_rows=batch["total_rows"],
                valid_rows=len(valid_records),
                rejected_rows=len(errors),
                duplicate_rows=batch["duplicate_count"],
                status="COMPLETED",
                imported_by_id=user_id,
                imported_by_username=username
            )
            db.add(history)
            db.flush()  # Populates history.id

            # 2. Insert Import Errors if any
            for err in errors:
                imp_err = ImportError(
                    import_history_id=history.id,
                    row_number=err["row_number"],
                    error_type=err["error_type"],
                    field_name=err.get("field_name"),
                    error_message=err["error_message"],
                    raw_data=err.get("raw_data")
                )
                db.add(imp_err)

            # 3. Insert Business Records
            if file_type == "PRODUCTION":
                for rec_data in valid_records:
                    rec = ProductionRecord(
                        date=rec_data["date"],
                        machine_id=rec_data["machine_id"],
                        frame_id=rec_data["frame_id"],
                        shift_id=rec_data["shift_id"],
                        customer_id=rec_data["customer_id"],
                        operator_id=rec_data["operator_id"],
                        supervisor_id=rec_data["supervisor_id"],
                        static_time=rec_data["static_time"],
                        mounting_time=rec_data["mounting_time"],
                        rotational_time=rec_data["rotational_time"],
                        dismantling_time=rec_data["dismantling_time"],
                        total_testing_time=rec_data["total_testing_time"],
                        cycle_time_hours=rec_data["cycle_time_hours"],
                        test_result=rec_data["test_result"],
                        nc_raised=rec_data["nc_raised"],
                        rework_time=rec_data["rework_time"],
                        approval_status=ApprovalStatusEnum.APPROVED.value, # Historical data imported as APPROVED
                        notes=rec_data.get("notes")
                    )
                    db.add(rec)
            else:
                # QUALITY & NC
                for q_data in valid_records:
                    # Sequential NC Number
                    year = datetime.now(timezone.utc).year
                    count = db.query(NCRecord).count() + 1
                    nc_num = f"NC-{year}-{str(count).zfill(4)}"

                    # Quality Record
                    q_rec = QualityRecord(
                        machine_id=q_data["machine_id"],
                        defect_description=q_data["defect_description"],
                        defect_category=q_data["defect_category"],
                        date_of_occurrence=q_data["date_of_occurrence"],
                        responsible_department=q_data["responsible_department"],
                        severity=q_data["severity"],
                        rework_minutes=q_data["rework_minutes"],
                        created_by_id=user_id
                    )
                    db.add(q_rec)
                    db.flush()

                    # NC Record
                    nc_rec = NCRecord(
                        nc_number=nc_num,
                        quality_record_id=q_rec.id,
                        machine_id=q_data["machine_id"],
                        title=f"Imported Defect: {q_data['defect_category']}",
                        description=q_data["defect_description"],
                        defect_category=q_data["defect_category"],
                        classification=q_data["classification"],
                        responsible_department=q_data["responsible_department"],
                        quality_engineer_id=user_id,
                        status=q_data["status"],
                        root_cause=q_data.get("root_cause"),
                        corrective_action=q_data.get("corrective_action")
                    )
                    db.add(nc_rec)

            db.commit()

            # 4. Audit Log
            log_audit(
                db=db,
                action="IMPORT",
                module="IMPORT",
                record_id=str(history.id),
                username=username,
                user_id=user_id,
                role=role,
                new_values={
                    "file_name": file_name,
                    "file_type": file_type,
                    "imported_records": len(valid_records),
                    "rejected_rows": len(errors),
                    "duplicates": batch["duplicate_count"]
                },
                ip_address=ip_address
            )

            # Evict batch from cache
            BATCH_CACHE.pop(batch_id, None)

            return ImportConfirmResponse(
                import_history_id=history.id,
                file_name=file_name,
                file_type=file_type,
                imported_records_count=len(valid_records),
                rejected_records_count=len(errors),
                duplicate_records_count=batch["duplicate_count"],
                status="COMPLETED",
                message=f"Successfully imported {len(valid_records)} records into the database. {len(errors)} invalid/duplicate rows were safely logged."
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Import transaction failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database transaction error during import: {str(e)}"
            )

    @classmethod
    def get_import_history(cls, db: Session, limit: int = 50) -> List[ImportHistory]:
        return db.query(ImportHistory).order_by(ImportHistory.id.desc()).limit(limit).all()

    @classmethod
    def get_import_errors(cls, db: Session, history_id: int) -> List[ImportError]:
        return db.query(ImportError).filter(ImportError.import_history_id == history_id).order_by(ImportError.row_number.asc()).all()

    @classmethod
    def export_production_to_excel(
        cls,
        db: Session,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        machine_id: Optional[int] = None,
        status_val: Optional[str] = None
    ) -> io.BytesIO:
        """Exports filtered production records to an Excel workbook using Pandas."""
        query = db.query(ProductionRecord)
        if start_date:
            query = query.filter(ProductionRecord.date >= start_date)
        if end_date:
            query = query.filter(ProductionRecord.date <= end_date)
        if machine_id:
            query = query.filter(ProductionRecord.machine_id == machine_id)
        if status_val:
            query = query.filter(ProductionRecord.approval_status == status_val.upper())

        records = query.order_by(ProductionRecord.date.desc(), ProductionRecord.id.desc()).all()

        rows = []
        for r in records:
            rows.append({
                "Record ID": r.id,
                "Date": str(r.date),
                "Machine Code": r.machine.machine_code if r.machine else f"M-{r.machine_id}",
                "Machine Name": r.machine.name if r.machine else "",
                "Frame": r.frame.frame_code if r.frame else "",
                "Shift": r.shift.shift_name if r.shift else "",
                "Customer": r.customer.customer_name if r.customer else "",
                "Operator": r.operator.full_name if r.operator else "",
                "Supervisor": r.supervisor.full_name if r.supervisor else "",
                "Static Time (min)": r.static_time,
                "Mounting Time (min)": r.mounting_time,
                "Rotational Time (min)": r.rotational_time,
                "Dismantling Time (min)": r.dismantling_time,
                "Total Testing Time (min)": r.total_testing_time,
                "Cycle Time (hours)": r.cycle_time_hours,
                "Test Result": r.test_result,
                "NC Raised": "Yes" if r.nc_raised else "No",
                "Rework Time (min)": r.rework_time,
                "Approval Status": r.approval_status,
                "Notes": r.notes or ""
            })

        df = pd.DataFrame(rows)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Production Records")
        output.seek(0)
        return output

    @classmethod
    def export_quality_to_excel(
        cls,
        db: Session,
        status_val: Optional[str] = None,
        classification: Optional[str] = None
    ) -> io.BytesIO:
        """Exports filtered quality and NC records to an Excel workbook using Pandas."""
        query = db.query(NCRecord)
        if status_val:
            query = query.filter(NCRecord.status == status_val.upper())
        if classification:
            query = query.filter(NCRecord.classification == classification.upper())

        ncs = query.order_by(NCRecord.id.desc()).all()

        rows = []
        for nc in ncs:
            total_rework = sum(r.rework_minutes for r in nc.rework_records)
            rows.append({
                "NC Number": nc.nc_number,
                "Machine Code": nc.machine.machine_code if nc.machine else f"M-{nc.machine_id}",
                "Title": nc.title,
                "Defect Category": nc.defect_category,
                "Classification": nc.classification,
                "Status": nc.status,
                "Responsible Department": nc.responsible_department,
                "Quality Engineer": nc.quality_engineer.full_name if nc.quality_engineer else "",
                "Total Rework (min)": total_rework,
                "Root Cause": nc.root_cause or "",
                "Corrective Action": nc.corrective_action or "",
                "Preventive Action": nc.preventive_action or "",
                "Closure Notes": nc.closure_notes or "",
                "Date Created": str(nc.created_at.date()) if nc.created_at else ""
            })

        df = pd.DataFrame(rows)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="NC Quality Records")
        output.seek(0)
        return output
