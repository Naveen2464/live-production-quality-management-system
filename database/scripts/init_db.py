import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.db.session import engine, SessionLocal, Base
from app.models.all_models import Role, User, Shift, Frame, Machine, Customer
from app.core.security import get_password_hash


def init_db():
    print(f"Creating all database tables using engine: {engine.url}...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

    db = SessionLocal()
    try:
        # Check if roles already exist
        if db.query(Role).count() == 0:
            print("Seeding roles...")
            roles_data = [
                Role(id=1, name="Administrator", description="Full system administration, user management, master data control"),
                Role(id=2, name="Supervisor", description="Production review, record approval, shift monitoring"),
                Role(id=3, name="Quality Engineer", description="NC case management, defect tracking, rework verification and closure"),
                Role(id=4, name="Management", description="Executive dashboard review, Power BI analytics, reports"),
                Role(id=5, name="Operator", description="Daily production testing data entry, personal submission history"),
            ]
            db.add_all(roles_data)
            db.commit()
            print("Roles seeded successfully.")

        # Check shifts
        if db.query(Shift).count() == 0:
            print("Seeding shifts...")
            shifts_data = [
                Shift(id=1, shift_name="Shift A", start_time="06:00", end_time="14:00", description="Morning shift (06:00 to 14:00)"),
                Shift(id=2, shift_name="Shift B", start_time="14:00", end_time="22:00", description="Afternoon shift (14:00 to 22:00)"),
                Shift(id=3, shift_name="Shift C", start_time="22:00", end_time="06:00", description="Night shift (22:00 to 06:00)"),
            ]
            db.add_all(shifts_data)
            db.commit()
            print("Shifts seeded.")

        # Check frames
        if db.query(Frame).count() == 0:
            print("Seeding frames...")
            frames_data = [
                Frame(id=1, frame_code="FR-063", frame_name="Frame 63", description="Frame size 63mm shaft height"),
                Frame(id=2, frame_code="FR-071", frame_name="Frame 71", description="Frame size 71mm shaft height"),
                Frame(id=3, frame_code="FR-080", frame_name="Frame 80", description="Frame size 80mm shaft height"),
                Frame(id=4, frame_code="FR-090", frame_name="Frame 90", description="Frame size 90mm shaft height"),
                Frame(id=5, frame_code="FR-100", frame_name="Frame 100", description="Frame size 100mm shaft height"),
                Frame(id=6, frame_code="FR-112", frame_name="Frame 112", description="Frame size 112mm shaft height"),
                Frame(id=7, frame_code="FR-132", frame_name="Frame 132", description="Frame size 132mm shaft height"),
            ]
            db.add_all(frames_data)
            db.commit()
            print("Frames seeded.")

        # Check machines
        if db.query(Machine).count() == 0:
            print("Seeding machines...")
            machines_data = [
                Machine(id=1, machine_code="M-101", name="Test Bed 01 - Dyno Alpha", model="TD-250kW", line_name="Line 1 - Heavy Motors"),
                Machine(id=2, machine_code="M-102", name="Test Bed 02 - Dyno Beta", model="TD-250kW", line_name="Line 1 - Heavy Motors"),
                Machine(id=3, machine_code="M-103", name="Test Bed 03 - High Speed", model="TD-400kW", line_name="Line 2 - Precision Motors"),
                Machine(id=4, machine_code="M-201", name="Rotational Rig 01", model="RR-100", line_name="Line 2 - Precision Motors"),
                Machine(id=5, machine_code="M-202", name="Rotational Rig 02", model="RR-150", line_name="Line 3 - Standard Motors"),
                Machine(id=6, machine_code="M-301", name="Static Inspection Bench 01", model="SB-50", line_name="Line 3 - Standard Motors"),
            ]
            db.add_all(machines_data)
            db.commit()
            print("Machines seeded.")

        # Check customers
        if db.query(Customer).count() == 0:
            print("Seeding customers...")
            customers_data = [
                Customer(id=1, customer_code="CUST-ABB", customer_name="ABB Power & Industrial Grids", contact_person="Ramesh Sharma", email="ramesh.sharma@abb.com", phone="+91 9876543210"),
                Customer(id=2, customer_code="CUST-SIEM", customer_name="Siemens Energy India", contact_person="Kavita Nair", email="kavita.nair@siemens.com", phone="+91 9876543211"),
                Customer(id=3, customer_code="CUST-SCHN", customer_name="Schneider Electric Manufacturing", contact_person="Arun Patel", email="arun.patel@se.com", phone="+91 9876543212"),
                Customer(id=4, customer_code="CUST-DANF", customer_name="Danfoss Power Solutions", contact_person="Deepak Verma", email="deepak.v@danfoss.com", phone="+91 9876543213"),
                Customer(id=5, customer_code="CUST-KIRL", customer_name="Kirloskar Electric Co.", contact_person="Sanjay Rao", email="sanjay.rao@kirloskar.com", phone="+91 9876543214"),
            ]
            db.add_all(customers_data)
            db.commit()
            print("Customers seeded.")

        # Check users
        if db.query(User).count() == 0:
            print("Seeding initial users...")
            common_hash = get_password_hash("Admin@123")
            users_data = [
                User(id=1, username="admin", full_name="System Administrator", email="admin@nidec-system.com", hashed_password=common_hash, role_id=1, is_active=True, is_ad_user=False, department="IT & Systems"),
                User(id=2, username="supervisor_rajesh", full_name="Rajesh K. (Production Supervisor)", email="rajesh.k@nidec-system.com", hashed_password=common_hash, role_id=2, is_active=True, is_ad_user=False, department="Production Line 1"),
                User(id=3, username="operator_suresh", full_name="Suresh M. (Lead Operator)", email="suresh.m@nidec-system.com", hashed_password=common_hash, role_id=5, is_active=True, is_ad_user=False, department="Production Testing"),
                User(id=4, username="qe_priya", full_name="Priya S. (Senior Quality Engineer)", email="priya.s@nidec-system.com", hashed_password=common_hash, role_id=3, is_active=True, is_ad_user=False, department="Quality Assurance"),
                User(id=5, username="mgmt_vikram", full_name="Vikram Deshmukh (Plant General Manager)", email="mgmt.vikram@nidec-system.com", hashed_password=common_hash, role_id=4, is_active=True, is_ad_user=False, department="Plant Management"),
            ]
            db.add_all(users_data)
            db.commit()
            print("Initial users seeded.")

        print("Database initialization and initial seeding complete!")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()

