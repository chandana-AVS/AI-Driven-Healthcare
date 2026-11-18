from app.config import settings
from app.services import otp_service
from tests.conftest import API, PASSWORD, register_patient


def test_static_code_mode(client, monkeypatch):
    _, payload = register_patient(client, verify=False)
    monkeypatch.setattr(settings, "SMS_PROVIDER", "static")
    assert otp_service.static_mode()
    bad = client.post(f"{API}/auth/phone/verify", json={"identifier": payload["phone"], "code": "654321"})
    assert bad.status_code == 400
    ok = client.post(f"{API}/auth/phone/verify", json={"identifier": payload["phone"], "code": settings.OTP_STATIC_CODE})
    assert ok.status_code == 200
    login = client.post(f"{API}/auth/login", json={"identifier": payload["phone"], "password": PASSWORD})
    assert login.status_code == 200
