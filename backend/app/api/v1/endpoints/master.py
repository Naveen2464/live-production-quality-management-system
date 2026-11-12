from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.all_models import Machine, Frame, Shift, Customer, User, Role
from app.schemas.master import MasterDropdownsResponse, DropdownItem

router = APIRouter()


@router.get("/dropdowns", response_model=MasterDropdownsResponse, summary="Get all master dropdown lists")
def get_master_dropdowns(db: Session = Depends(get_db)):
    """Provides dropdown items for Machine, Frame, Shift, Customer, Operator, and Supervisor."""
    machines = db.query(Machine).filter(Machine.is_active == True).all()
    frames = db.query(Frame).filter(Frame.is_active == True).all()
    shifts = db.query(Shift).filter(Shift.is_active == True).all()
    customers = db.query(Customer).filter(Customer.is_active == True).all()
    
    # Operators (Role name 'Operator')
    operators = db.query(User).join(User.role).filter(
        Role.name == "Operator",
        User.is_active == True
    ).all()
    
    # Supervisors (Role name 'Supervisor' or 'Administrator')
    supervisors = db.query(User).join(User.role).filter(
        Role.name.in_(["Supervisor", "Administrator"]),
        User.is_active == True
    ).all()

    return MasterDropdownsResponse(
        machines=[DropdownItem(id=m.id, label=f"{m.machine_code} - {m.name}", code=m.machine_code, extra={"model": m.model or "", "line": m.line_name or ""}) for m in machines],
        frames=[DropdownItem(id=f.id, label=f"{f.frame_code} ({f.frame_name})", code=f.frame_code, extra={"name": f.frame_name}) for f in frames],
        shifts=[DropdownItem(id=s.id, label=f"{s.shift_name} ({s.start_time} - {s.end_time})", code=s.shift_name, extra={"start": s.start_time, "end": s.end_time}) for s in shifts],
        customers=[DropdownItem(id=c.id, label=f"{c.customer_name} ({c.customer_code})", code=c.customer_code, extra={"email": c.email or ""}) for c in customers],
        operators=[DropdownItem(id=u.id, label=f"{u.full_name} ({u.username})", code=u.username, extra={"department": u.department or ""}) for u in operators],
        supervisors=[DropdownItem(id=s.id, label=f"{s.full_name} ({s.username})", code=s.username, extra={"department": s.department or ""}) for s in supervisors]
    )

