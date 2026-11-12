import datetime as dt
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


# -------------------------------------------------------------
# QUALITY RECORD SCHEMAS
# -------------------------------------------------------------
class QualityRecordBase(BaseModel):
    production_record_id: Optional[int] = Field(None, description="Optional link to production test run")
    machine_id: int = Field(..., description="ID of machine/test bed")
    defect_description: str = Field(..., min_length=5, description="Detailed defect description")
    defect_category: str = Field(..., description="Category: Electrical, Mechanical, Calibration, Assembly, Frame Defect, Bearing Issue, Winding Defect")
    date_of_occurrence: dt.date = Field(..., description="Date defect was identified")
    responsible_department: str = Field(..., description="Department: Production, Quality Assurance, Maintenance, Assembly, R&D")
    severity: str = Field("MEDIUM", description="Severity: LOW, MEDIUM, HIGH, CRITICAL")
    rework_minutes: float = Field(0.0, ge=0, description="Estimated or logged rework time in minutes")


class QualityRecordCreate(QualityRecordBase):
    create_nc: bool = Field(True, description="Whether to automatically spawn a formal NC case")
    nc_classification: Optional[str] = Field("MAJOR", description="Classification for spawned NC: MINOR, MAJOR, CRITICAL")


class QualityRecordResponse(QualityRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by_id: int
    created_at: dt.datetime
    updated_at: dt.datetime
    
    # Associated master details
    machine_code: Optional[str] = None
    machine_name: Optional[str] = None
    created_by_name: Optional[str] = None
    nc_number: Optional[str] = None


# -------------------------------------------------------------
# REWORK SCHEMAS
# -------------------------------------------------------------
class ReworkRecordBase(BaseModel):
    nc_record_id: int = Field(..., description="Parent NC record ID")
    production_record_id: Optional[int] = Field(None, description="Optional production record ID")
    machine_id: int = Field(..., description="Machine ID")
    rework_minutes: float = Field(..., gt=0, description="Rework time in minutes")
    rework_description: str = Field(..., min_length=5, description="Description of corrective work performed")
    rework_done_by_id: int = Field(..., description="Technician who executed rework")
    verified_by_id: Optional[int] = Field(None, description="Engineer who verified rework")
    completion_date: Optional[dt.date] = None
    rework_status: str = Field("PENDING", description="PENDING, IN_PROGRESS, COMPLETED, VERIFIED")
    notes: Optional[str] = None


class ReworkRecordCreate(ReworkRecordBase):
    pass


class ReworkStatusUpdate(BaseModel):
    rework_status: str = Field(..., description="PENDING, IN_PROGRESS, COMPLETED, VERIFIED")
    verified_by_id: Optional[int] = None
    completion_date: Optional[dt.date] = None
    notes: Optional[str] = None


class ReworkRecordResponse(ReworkRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: dt.datetime
    updated_at: dt.datetime
    rework_done_by_name: Optional[str] = None
    verified_by_name: Optional[str] = None


# -------------------------------------------------------------
# NON-CONFORMANCE (NC) SCHEMAS
# -------------------------------------------------------------
class NCRecordBase(BaseModel):
    quality_record_id: Optional[int] = None
    production_record_id: Optional[int] = None
    machine_id: int = Field(..., description="Machine ID")
    title: str = Field(..., min_length=5, max_length=200, description="Summary title of the issue")
    description: str = Field(..., min_length=10, description="Full problem description")
    defect_category: str = Field(..., description="Category: Electrical, Mechanical, Calibration, Assembly, Frame Defect")
    classification: str = Field("MAJOR", description="MINOR, MAJOR, CRITICAL")
    responsible_department: str = Field(..., description="Responsible department")
    quality_engineer_id: int = Field(..., description="Assigned Quality Engineer user ID")


class NCRecordCreate(NCRecordBase):
    pass


class NCRecordUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    classification: Optional[str] = None
    responsible_department: Optional[str] = None
    quality_engineer_id: Optional[int] = None
    root_cause: Optional[str] = Field(None, description="Root Cause Analysis description")
    corrective_action: Optional[str] = Field(None, description="Corrective Action implemented")
    preventive_action: Optional[str] = Field(None, description="Preventive Action to avoid recurrence")


class NCStatusTransitionRequest(BaseModel):
    target_status: str = Field(..., description="OPEN, IN_PROGRESS, UNDER_REVIEW, CLOSED")
    user_id: int = Field(..., description="User ID performing transition")
    user_role: str = Field(..., description="Role of user performing transition")
    closure_notes: Optional[str] = Field(None, description="Mandatory when target_status is CLOSED")
    root_cause: Optional[str] = Field(None, description="Optional RCA update during transition")
    corrective_action: Optional[str] = Field(None, description="Optional CAPA update during transition")

    @model_validator(mode="after")
    def validate_closure_requirements(self) -> "NCStatusTransitionRequest":
        if self.target_status.upper() == "CLOSED":
            if not self.closure_notes or len(self.closure_notes.strip()) < 5:
                raise ValueError("Verification and closure notes (at least 5 characters) are mandatory to close an NC.")
            if self.user_role not in ["Quality Engineer", "Administrator"]:
                raise ValueError("Permission Denied: Only Quality Engineers and Administrators are authorized to close Non-Conformance cases.")
        return self


class NCRecordResponse(NCRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nc_number: str
    status: str
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    closed_at: Optional[dt.datetime] = None
    closed_by_id: Optional[int] = None
    closure_notes: Optional[str] = None
    created_at: dt.datetime
    updated_at: dt.datetime
    
    # Nested and extra descriptive fields
    machine_code: Optional[str] = None
    machine_name: Optional[str] = None
    quality_engineer_name: Optional[str] = None
    closed_by_name: Optional[str] = None
    total_rework_minutes: float = 0.0
    rework_records: List[ReworkRecordResponse] = []


class NCPaginationResponse(BaseModel):
    items: List[NCRecordResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

