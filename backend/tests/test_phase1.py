import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal, Base, engine
from app.models.all_models import Role, User, Machine, Customer, Frame, Shift
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token


@pytest.fixture(scope="module")
def client():
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Live Production & Quality Management System" in data["service"]


def test_db_health_endpoint(client):
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True


def test_password_hashing_and_verification():
    raw_pwd = "SecurePassword@2026"
    hashed = get_password_hash(raw_pwd)
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_generation_and_decoding():
    token = create_access_token(subject="admin", role="Administrator")
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["role"] == "Administrator"


def test_models_and_seed_data():
    db = SessionLocal()
    try:
        roles = db.query(Role).all()
        assert len(roles) >= 5
        role_names = [r.name for r in roles]
        assert "Administrator" in role_names
        assert "Supervisor" in role_names
        assert "Quality Engineer" in role_names
        assert "Operator" in role_names
        assert "Management" in role_names

        shifts = db.query(Shift).all()
        assert len(shifts) >= 3

        machines = db.query(Machine).all()
        assert len(machines) >= 6

        customers = db.query(Customer).all()
        assert len(customers) >= 5

        frames = db.query(Frame).all()
        assert len(frames) >= 7

        users = db.query(User).all()
        assert len(users) >= 5
    finally:
        db.close()

