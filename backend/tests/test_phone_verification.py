from datetime import timedelta

from app.config import settings
from app.database import SessionLocal
from app.models import PhoneOTP
from tests.conftest import API, PASSWORD, last_sms_code, login, register_patient


def _login(client, identifier):
    return client.post(f"{API}/auth/login", json={"identifier": identifier, "password": PASSWORD})


def _verify(client, identifier, code):
    return client.post(f"{API}/auth/phone/verify", json={"identifier": identifier, "code": code})


def _wrong(code: str) -> str:
    return "000000" if code != "000000" else "111111"


def test_registration_sends_sms_and_blocks_login_until_verified(client):
    res, payload = register_patient(client, verify=False)
    assert res.status_code == 201
    assert res.json()["phone_verified"] is False
    code = last_sms_code(payload["phone"])
    assert len(code) == settings.OTP_LENGTH and code.isdigit()

    blocked = _login(client, payload["email"])
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Phone number not verified"

    assert _verify(client, payload["phone"], code).status_code == 200
    login(client, payload["email"])
    login(client, payload["phone"])


def test_verify_by_email_identifier(client):
    _, payload = register_patient(client, verify=False)
    assert _verify(client, payload["email"], last_sms_code(payload["phone"])).status_code == 200


def test_otp_is_not_stored_in_plain_text(client):
    _, payload = register_patient(client, verify=False)
    code = last_sms_code(payload["phone"])
    with SessionLocal() as db:
        otp = db.query(PhoneOTP).one()
        assert code not in otp.code_hash and len(otp.code_hash) == 64


def test_wrong_code_and_attempt_limit(client):
    _, payload = register_patient(client, verify=False)
    code = last_sms_code(payload["phone"])
    for i in range(settings.OTP_MAX_ATTEMPTS):
        res = _verify(client, payload["phone"], _wrong(code))
        assert res.status_code == 400
    # Even the right code is refused once the attempts are used up.
    assert _verify(client, payload["phone"], code).status_code == 400
    assert _login(client, payload["email"]).status_code == 403


def test_expired_code_rejected(client):
    _, payload = register_patient(client, verify=False)
    code = last_sms_code(payload["phone"])
    with SessionLocal() as db:
        otp = db.query(PhoneOTP).one()
        otp.expires_at = otp.created_at - timedelta(seconds=1)
        db.commit()
    assert _verify(client, payload["phone"], code).status_code == 400


def test_resend_cooldown_and_new_code_replaces_old(client, monkeypatch):
    _, payload = register_patient(client, verify=False)
    first = last_sms_code(payload["phone"])
    res = client.post(f"{API}/auth/phone/send-otp", json={"identifier": payload["phone"]})
    assert res.status_code == 429 and "Retry-After" in res.headers

    monkeypatch.setattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 0)
    assert client.post(f"{API}/auth/phone/send-otp", json={"identifier": payload["phone"]}).status_code == 202
    second = last_sms_code(payload["phone"])
    if first != second:
        assert _verify(client, payload["phone"], first).status_code == 400  # old code no longer valid
    assert _verify(client, payload["phone"], second).status_code == 200


def test_hourly_send_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 0)
    _, payload = register_patient(client, verify=False)  # 1st code
    for _ in range(settings.OTP_MAX_PER_HOUR - 1):
        assert client.post(f"{API}/auth/phone/send-otp", json={"identifier": payload["phone"]}).status_code == 202
    assert client.post(f"{API}/auth/phone/send-otp", json={"identifier": payload["phone"]}).status_code == 429


def test_send_otp_does_not_reveal_unknown_accounts(client):
    res = client.post(f"{API}/auth/phone/send-otp", json={"identifier": "9000000001"})
    assert res.status_code == 202
    assert _verify(client, "9000000001", "123456").status_code == 400


def test_changing_phone_requires_reverification(client, patient):
    new_phone = "9123400000"
    res = client.patch(f"{API}/users/me", headers=patient["headers"], json={"phone": new_phone})
    assert res.status_code == 200 and res.json()["phone_verified"] is False
    assert _login(client, patient["payload"]["email"]).status_code == 403
    assert _verify(client, new_phone, last_sms_code(new_phone)).status_code == 200
    login(client, new_phone)
