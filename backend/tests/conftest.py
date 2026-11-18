"""Test fixtures: isolated SQLite database + temporary storage directory per test."""
import os
import tempfile
import uuid

# Configure environment BEFORE importing the app.
_TMP = tempfile.mkdtemp(prefix="hc_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TMP, 'test.db')}"
os.environ["STORAGE_PATH"] = os.path.join(_TMP, "storage")
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["MAX_UPLOAD_SIZE_MB"] = "1"
os.environ["SMS_PROVIDER"] = "console"  # random codes, read from the outbox

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import HealthcareWorkerProfile, User  # noqa: E402
from app.services.sms_service import get_sms_provider, to_e164  # noqa: E402
from app.utils.security import hash_password  # noqa: E402
from app.utils.validators import normalize_phone  # noqa: E402

API = "/api/v1"
PASSWORD = "SecurePassword123"

PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


@pytest.fixture(autouse=True)
def _db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    get_sms_provider().outbox.clear()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _uniq() -> str:
    return uuid.uuid4().hex[:8]


def last_sms_code(phone: str) -> str:
    """Read the most recent code the dev (console) SMS provider 'sent' to this number."""
    to = to_e164(normalize_phone(phone))
    for dest, body in reversed(get_sms_provider().outbox):
        if dest == to:
            return body.split()[0]
    raise AssertionError(f"no SMS sent to {to}")


def verify_phone(client, phone: str):
    res = client.post(f"{API}/auth/phone/verify", json={"identifier": phone, "code": last_sms_code(phone)})
    assert res.status_code == 200, res.text


def _register(client, url, payload, verify):
    res = client.post(url, json=payload)
    if verify and res.status_code == 201:
        verify_phone(client, payload["phone"])
    return res, payload


def register_patient(client, verify=True, **overrides):
    tag = _uniq()
    payload = {
        "full_name": f"Patient {tag}",
        "email": f"patient_{tag}@example.com",
        "phone": f"98{int(tag, 16) % 10**8:08d}",
        "password": PASSWORD,
        "preferred_language": "te",
    }
    payload.update(overrides)
    return _register(client, f"{API}/auth/register/patient", payload, verify)


def register_worker(client, verify=True, **overrides):
    tag = _uniq()
    payload = {
        "full_name": f"Worker {tag}",
        "email": f"worker_{tag}@example.com",
        "phone": f"97{int(tag, 16) % 10**8:08d}",
        "password": PASSWORD,
        "designation": "Nurse",
        "organization": "Primary Health Centre",
        "preferred_language": "hi",
    }
    payload.update(overrides)
    return _register(client, f"{API}/auth/register/healthcare-worker", payload, verify)


def login(client, identifier, password=PASSWORD) -> dict:
    res = client.post(f"{API}/auth/login", json={"identifier": identifier, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def patient(client):
    res, payload = register_patient(client)
    assert res.status_code == 201, res.text
    headers = login(client, payload["email"])
    me = client.get(f"{API}/patients/me", headers=headers).json()
    return {"headers": headers, "payload": payload, "user_id": me["user"]["id"], "patient_id": me["profile"]["id"]}


@pytest.fixture
def other_patient(client):
    res, payload = register_patient(client)
    headers = login(client, payload["email"])
    me = client.get(f"{API}/patients/me", headers=headers).json()
    return {"headers": headers, "payload": payload, "user_id": me["user"]["id"], "patient_id": me["profile"]["id"]}


def _make_worker(client, verified: bool):
    res, payload = register_worker(client)
    assert res.status_code == 201, res.text
    if verified:
        with SessionLocal() as db:
            prof = db.query(HealthcareWorkerProfile).join(User).filter(User.email == payload["email"]).one()
            prof.verification_status = "VERIFIED"
            prof.user.is_verified = True
            db.commit()
    headers = login(client, payload["email"])
    me = client.get(f"{API}/healthcare-workers/me", headers=headers).json()
    return {"headers": headers, "payload": payload, "worker_id": me["profile"]["id"]}


@pytest.fixture
def worker(client):
    return _make_worker(client, verified=True)


@pytest.fixture
def unverified_worker(client):
    return _make_worker(client, verified=False)


@pytest.fixture
def admin(client):
    with SessionLocal() as db:
        db.add(User(full_name="Admin", email="admin@example.com", password_hash=hash_password(PASSWORD),
                    role="ADMIN", preferred_language="en", is_active=True, is_verified=True))
        db.commit()
    return {"headers": login(client, "admin@example.com")}


def grant(client, patient, worker):
    res = client.post(f"{API}/patients/me/access", headers=patient["headers"],
                      json={"healthcare_worker_id": worker["worker_id"]})
    assert res.status_code == 201, res.text
    return res.json()


def upload(client, headers, url=f"{API}/patients/me/documents", name="rx.pdf", content=PDF_BYTES,
           mime="application/pdf", document_type="PRESCRIPTION", **form):
    data = {"document_type": document_type, **form}
    return client.post(url, headers=headers, files={"file": (name, content, mime)}, data=data)
