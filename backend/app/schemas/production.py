import datetime as dt
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ProductionRecordBase(BaseModel):
    date: dt.date = Field(..., description="Date of testing")
    machine_id: int = Field(..., description="ID of the machine/test bed")
    frame_id: int = Field(..., description="ID of the motor frame")
    shift_id: int = Field(..., description="ID of the work shift")
    operator_id: int = Field(..., description="ID of the operating technician")
    supervisor_id: int = Field(..., description="ID of the supervising engineer")
    customer_id: int = Field(..., description="ID of the client/customer")
    
    # Timing inputs in minutes
    static_time: float = Field(..., ge=0, description="Static testing time in minutes")
    mounting_time: float = Field(..., ge=0, description="Mounting time in minutes")
    rotational_time: float = Field(..., ge=0, description="Rotational testing time in minutes")
    dismantling_time: float = Field(..., ge=0, description="Dismantling time in minutes")
    
    # Optional client-provided calculations (will be verified/overridden by backend)
    total_testing_time: Optional[float] = Field(None, ge=0, description="Total testing time in minutes")
    cycle_time_hours: Optional[float] = Field(None, ge=0, description="Cycle time in hours")
    
    test_result: str = Field("PASS", description="Test outcome: PASS, FAIL, CONDITIONAL")
    nc_raised: bool = Field(False, description="Whether non-conformance was raised")
    rework_time: float = Field(0.0, ge=0, description="Rework time in minutes")
    notes: Optional[str] = Field(None, description="Optional operator notes")

    @model_validator(mode="after")
    def compute_and_validate_times(self) -> "ProductionRecordBase":
        calc_total = round(self.static_time + self.mounting_time + self.rotational_time + self.dismantling_time, 2)
        calc_hours = round(calc_total / 60.0, 4)
        
        # Always enforce backend calculations
        self.total_testing_time = calc_total
        self.cycle_time_hours = calc_hours
        return self


class ProductionRecordCreate(ProductionRecordBase):
    pass


class ProductionRecordUpdate(BaseModel):
    date: Optional[dt.date] = None
    machine_id: Optional[int] = None
    frame_id: Optional[int] = None
    shift_id: Optional[int] = None
    operator_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    customer_id: Optional[int] = None
    static_time: Optional[float] = Field(None, ge=0)
    mounting_time: Optional[float] = Field(None, ge=0)
    rotational_time: Optional[float] = Field(None, ge=0)
    dismantling_time: Optional[float] = Field(None, ge=0)
    test_result: Optional[str] = None
    nc_raised: Optional[bool] = None
    rework_time: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class ProductionApprovalRequest(BaseModel):
    action: str = Field(..., description="'APPROVE' or 'REJECT'")
    supervisor_id: int = Field(..., description="ID of supervisor taking action")
    rejection_reason: Optional[str] = Field(None, description="Mandatory if action is REJECT")

    @model_validator(mode="after")
    def validate_rejection(self) -> "ProductionApprovalRequest":
        if self.action.upper() == "REJECT" and not self.rejection_reason:
            raise ValueError("rejection_reason is required when rejecting a production record")
        return self


class MachineBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    machine_code: str
    name: str


class CustomerBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_code: str
    customer_name: str


class FrameBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    frame_code: str
    frame_name: str


class ShiftBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    shift_name: str
    start_time: str
    end_time: str


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str


class ProductionRecordResponse(ProductionRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    approval_status: str
    approved_by_id: Optional[int] = None
    approved_at: Optional[dt.datetime] = None
    rejection_reason: Optional[str] = None
    created_at: dt.datetime
    updated_at: dt.datetime
    
    # Associated master details
    machine: Optional[MachineBrief] = None
    frame: Optional[FrameBrief] = None
    shift: Optional[ShiftBrief] = None
    operator: Optional[UserBrief] = None
    supervisor: Optional[UserBrief] = None
    customer: Optional[CustomerBrief] = None


class ProductionPaginationResponse(BaseModel):
    items: List[ProductionRecordResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int
