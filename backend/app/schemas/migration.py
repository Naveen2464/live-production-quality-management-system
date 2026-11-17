import datetime as dt
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ImportErrorItem(BaseModel):
    row_number: int
    error_type: str
    field_name: Optional[str] = None
    error_message: str
    raw_data: Optional[Dict[str, Any]] = None


class ImportValidateResponse(BaseModel):
    batch_id: str
    file_name: str
    file_type: str
    detected_sheet: str
    detected_columns: List[str]
    mapped_columns: Dict[str, str]
    total_rows: int
    valid_count: int
    rejected_count: int
    duplicate_count: int
    sample_valid_rows: List[Dict[str, Any]] = []
    rejected_rows: List[ImportErrorItem] = []
    can_commit: bool


class ImportConfirmRequest(BaseModel):
    batch_id: str
    user_id: int = Field(1, description="User performing import")
    username: str = Field("admin", description="Username performing import")
    role: str = Field("Administrator", description="Role")


class ImportConfirmResponse(BaseModel):
    import_history_id: int
    file_name: str
    file_type: str
    imported_records_count: int
    rejected_records_count: int
    duplicate_records_count: int
    status: str
    message: str


class ImportHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_name: str
    file_type: str
    total_rows: int
    valid_rows: int
    rejected_rows: int
    duplicate_rows: int
    status: str
    imported_by_username: str
    created_at: dt.datetime

