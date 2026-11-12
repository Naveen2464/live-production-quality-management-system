from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.all_models import AuditLog


def log_audit(
    db: Session,
    action: str,
    module: str,
    record_id: str,
    username: str,
    user_id: Optional[int] = None,
    role: Optional[str] = None,
    previous_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AuditLog:
    """Creates an immutable audit log record."""
    audit_entry = AuditLog(
        user_id=user_id,
        username=username,
        role=role,
        action=action,
        module=module,
        record_id=str(record_id),
        previous_values=previous_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry

