from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from tests.conftest import API, PASSWORD, login, register_patient, register_worker


def test_patient_registration(client):
    res, payload = register_patient(client)
    assert res.status_code == 201
    body = res.json()
    assert body["role"] == "PATIENT"
    assert body["preferred_language"] == "te"
    assert "password" not in body and "password_hash" not in body


def test_healthcare_worker_registration(client):
    res, payload = register_worker(client)
    assert res.status_code == 201
    assert res.json()["role"] == "HEALTHCARE_WORKER"
    headers = login(client, payload["email"])
    me = client.get(f"{API}/healthcare-workers/me", headers=headers).json()
    assert me["profile"]["verification_status"] == "PENDING"
    assert me["profile"]["designation"] == "Nurse"


def test_registration_requires_phone(client):
    res, _ = register_patient(client, phone=None)
    assert res.status_code == 422
    res, _ = register_patient(client, phone="")
    assert res.status_code == 422


def test_registration_email_is_optional(client):
    res, payload = register_patient(client, email=None)
    assert res.status_code == 201, res.text
    assert res.json()["email"] is None
    login(client, payload["phone"])


def test_registration_rejects_weak_password(client):
    res, _ = register_patient(client, password="short")
    assert res.status_code == 422


def test_registration_rejects_unsupported_language(client):
    res, _ = register_patient(client, preferred_language="fr")
    assert res.status_code == 422


def test_registration_cannot_set_role(client):
    res, _ = register_patient(client, role="ADMIN")
    assert res.status_code == 422


def test_duplicate_registration_rejected(client):
    res, payload = register_patient(client)
    assert res.status_code == 201
    dup, _ = register_patient(client, email=payload["email"].upper())
    assert dup.status_code == 409
    dup_phone, _ = register_worker(client, phone=payload["phone"])
    assert dup_phone.status_code == 409


def test_login_with_email_and_phone(client):
    _, payload = register_patient(client)
    res = client.post(f"{API}/auth/login", json={"identifier": payload["email"], "password": PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "PATIENT"
    assert body["user"]["full_name"] == payload["full_name"]
    res2 = client.post(f"{API}/auth/login", json={"identifier": payload["phone"], "password": PASSWORD})
    assert res2.status_code == 200


def test_invalid_password_rejected(client):
    _, payload = register_patient(client)
    res = client.post(f"{API}/auth/login", json={"identifier": payload["email"], "password": "WrongPass999"})
    assert res.status_code == 401
    unknown = client.post(f"{API}/auth/login", json={"identifier": "nobody@example.com", "password": PASSWORD})
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == res.json()["detail"]  # no user enumeration


def test_jwt_validation(client):
    assert client.get(f"{API}/users/me").status_code == 401
    assert client.get(f"{API}/users/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401
    forged = jwt.encode({"sub": "x", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), "type": "access"},
                        "wrong-secret-wrong-secret-wrong-secret", algorithm="HS256")
    assert client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_expired_token_rejected(client):
    _, payload = register_patient(client)
    headers = login(client, payload["email"])
    user_id = client.get(f"{API}/users/me", headers=headers).json()["id"]
    expired = jwt.encode(
        {"sub": user_id, "role": "PATIENT", "type": "access",
         "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )
    res = client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Token has expired"


def test_deactivated_user_cannot_login(client, admin):
    _, payload = register_patient(client)
    headers = login(client, payload["email"])
    user_id = client.get(f"{API}/users/me", headers=headers).json()["id"]
    res = client.patch(f"{API}/admin/users/{user_id}/status", headers=admin["headers"], json={"is_active": False})
    assert res.status_code == 200
    assert client.get(f"{API}/users/me", headers=headers).status_code == 403
    res = client.post(f"{API}/auth/login", json={"identifier": payload["email"], "password": PASSWORD})
    assert res.status_code == 403
