import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Text, Date, DateTime,
    ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.db.session import Base


class ApprovalStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TestResultEnum(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    CONDITIONAL = "CONDITIONAL"


class NCClassificationEnum(str, enum.Enum):
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"


class NCStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLOSED = "CLOSED"


class ReworkStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"


# 1. ROLES TABLE
class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # Operator, Supervisor, Quality Engineer, Management, Administrator
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    users = relationship("User", back_populates="role")


# 2. USERS TABLE
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_ad_user = Column(Boolean, default=False, nullable=False)
    department = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    role = relationship("Role", back_populates="users")


# 3. MACHINES TABLE
class Machine(Base):
    __tablename__ = "machines"
    
    id = Column(Integer, primary_key=True, index=True)
    machine_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    model = Column(String(100), nullable=True)
    line_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# 4. CUSTOMERS TABLE
class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(100), unique=True, nullable=False, index=True)
    customer_name = Column(String(200), nullable=False, index=True)
    contact_person = Column(String(150), nullable=True)
    email = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# 5. FRAMES TABLE
class Frame(Base):
    __tablename__ = "frames"
    
    id = Column(Integer, primary_key=True, index=True)
    frame_code = Column(String(100), unique=True, nullable=False, index=True)
    frame_name = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# 6. SHIFTS TABLE
class Shift(Base):
    __tablename__ = "shifts"
    
    id = Column(Integer, primary_key=True, index=True)
    shift_name = Column(String(50), unique=True, nullable=False)  # Shift A, Shift B, Shift C
    start_time = Column(String(10), nullable=False)               # "06:00"
    end_time = Column(String(10), nullable=False)                 # "14:00"
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# 7. PRODUCTION RECORDS TABLE
class ProductionRecord(Base):
    __tablename__ = "production_records"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False, index=True)
    frame_id = Column(Integer, ForeignKey("frames.id"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False, index=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Timing fields in minutes
    static_time = Column(Float, default=0.0, nullable=False)
    mounting_time = Column(Float, default=0.0, nullable=False)
    rotational_time = Column(Float, default=0.0, nullable=False)
    dismantling_time = Column(Float, default=0.0, nullable=False)
    
    # Calculated fields
    total_testing_time = Column(Float, default=0.0, nullable=False)  # static + mounting + rotational + dismantling
    cycle_time_hours = Column(Float, default=0.0, nullable=False)    # total_testing_time / 60
    
    # Quality indicators
    test_result = Column(String(50), default="PASS", nullable=False) # PASS, FAIL, CONDITIONAL
    nc_raised = Column(Boolean, default=False, nullable=False, index=True)
    rework_time = Column(Float, default=0.0, nullable=False)         # in minutes
    
    # Workflow
    approval_status = Column(String(50), default="PENDING", nullable=False, index=True) # PENDING, APPROVED, REJECTED
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    machine = relationship("Machine")
    frame = relationship("Frame")
    shift = relationship("Shift")
    operator = relationship("User", foreign_keys=[operator_id])
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    customer = relationship("Customer")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    quality_records = relationship("QualityRecord", back_populates="production_record")
    nc_records = relationship("NCRecord", back_populates="production_record")


# 8. QUALITY RECORDS TABLE
class QualityRecord(Base):
    __tablename__ = "quality_records"
    
    id = Column(Integer, primary_key=True, index=True)
    production_record_id = Column(Integer, ForeignKey("production_records.id"), nullable=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False, index=True)
    defect_description = Column(Text, nullable=False)
    defect_category = Column(String(100), nullable=False, index=True)  # Electrical, Mechanical, Calibration, Assembly, Frame Defect
    date_of_occurrence = Column(Date, nullable=False, index=True)
    responsible_department = Column(String(100), nullable=False, index=True) # Production, Maintenance, QA, R&D, Assembly
    severity = Column(String(50), default="MEDIUM", nullable=False)
    rework_minutes = Column(Float, default=0.0, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    production_record = relationship("ProductionRecord", back_populates="quality_records")
    machine = relationship("Machine")
    created_by = relationship("User")
    nc_record = relationship("NCRecord", uselist=False, back_populates="quality_record")


# 9. NC RECORDS TABLE (Non-conformance)
class NCRecord(Base):
    __tablename__ = "nc_records"
    
    id = Column(Integer, primary_key=True, index=True)
    nc_number = Column(String(50), unique=True, nullable=False, index=True) # e.g. NC-2026-0001
    quality_record_id = Column(Integer, ForeignKey("quality_records.id"), nullable=True)
    production_record_id = Column(Integer, ForeignKey("production_records.id"), nullable=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False, index=True)
    
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    defect_category = Column(String(100), nullable=False)
    classification = Column(String(50), default="MAJOR", nullable=False) # MINOR, MAJOR, CRITICAL
    responsible_department = Column(String(100), nullable=False)
    quality_engineer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    status = Column(String(50), default="OPEN", nullable=False, index=True) # OPEN, IN_PROGRESS, UNDER_REVIEW, CLOSED
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    preventive_action = Column(Text, nullable=True)
    
    closed_at = Column(DateTime, nullable=True)
    closed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    closure_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    quality_record = relationship("QualityRecord", back_populates="nc_record")
    production_record = relationship("ProductionRecord", back_populates="nc_records")
    machine = relationship("Machine")
    quality_engineer = relationship("User", foreign_keys=[quality_engineer_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])
    rework_records = relationship("ReworkRecord", back_populates="nc_record")


# 10. REWORK RECORDS TABLE
class ReworkRecord(Base):
    __tablename__ = "rework_records"
    
    id = Column(Integer, primary_key=True, index=True)
    nc_record_id = Column(Integer, ForeignKey("nc_records.id"), nullable=False, index=True)
    production_record_id = Column(Integer, ForeignKey("production_records.id"), nullable=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    
    rework_minutes = Column(Float, nullable=False, default=0.0)
    rework_description = Column(Text, nullable=False)
    rework_done_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    completion_date = Column(Date, nullable=True)
    
    rework_status = Column(String(50), default="PENDING", nullable=False) # PENDING, IN_PROGRESS, COMPLETED, VERIFIED
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    nc_record = relationship("NCRecord", back_populates="rework_records")
    rework_done_by = relationship("User", foreign_keys=[rework_done_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])


# 11. AUDIT LOGS TABLE
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String(100), nullable=False, index=True)
    role = Column(String(50), nullable=True)
    action = Column(String(50), nullable=False, index=True) # CREATE, UPDATE, DELETE, APPROVE, REJECT, CLOSE, IMPORT
    module = Column(String(50), nullable=False, index=True) # PRODUCTION, QUALITY, NC, REWORK, USER, ADMIN, IMPORT
    record_id = Column(String(50), nullable=True)
    
    previous_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


# 12. IMPORT HISTORY TABLE
class ImportHistory(Base):
    __tablename__ = "import_history"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # PRODUCTION, QUALITY
    total_rows = Column(Integer, default=0, nullable=False)
    valid_rows = Column(Integer, default=0, nullable=False)
    rejected_rows = Column(Integer, default=0, nullable=False)
    duplicate_rows = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="COMPLETED", nullable=False) # VALIDATED, COMPLETED, FAILED
    imported_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    imported_by_username = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    errors = relationship("ImportError", back_populates="import_batch", cascade="all, delete-orphan")
    imported_by = relationship("User")


# 13. IMPORT ERRORS TABLE
class ImportError(Base):
    __tablename__ = "import_errors"
    
    id = Column(Integer, primary_key=True, index=True)
    import_history_id = Column(Integer, ForeignKey("import_history.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    raw_data = Column(JSON, nullable=True)
    error_type = Column(String(100), nullable=False) # VALIDATION_ERROR, DUPLICATE, MISSING_RELATION, FORMAT_ERROR
    error_message = Column(Text, nullable=False)
    field_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    import_batch = relationship("ImportHistory", back_populates="errors")


