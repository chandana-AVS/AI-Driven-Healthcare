import uuid

from tests.conftest import API, PASSWORD, _register, login


def register_admin(client, verify=True, **overrides):
    tag = uuid.uuid4().hex[:8]
    payload = {
        "full_name": f"Admin {tag}",
        "email": f"admin_{tag}@example.com",
        "phone": f"96{int(tag, 16) % 10**8:08d}",
        "password": PASSWORD,
        "preferred_language": "en",
        "employee_id": f"emp-{tag}",
        "hospital_name": "District  Hospital Guntur",
    }
    payload.update(overrides)
    return _register(client, f"{API}/auth/register/admin", payload, verify)


def test_admin_registration_creates_pending_admin(client):
    res, payload = register_admin(client)
    assert res.status_code == 201, res.text
    assert res.json()["role"] == "ADMIN"
    assert res.json()["is_verified"] is False
    headers = login(client, payload["email"])
    me = client.get(f"{API}/admin/me", headers=headers).json()
    assert me["verification_status"] == "PENDING"
    assert me["profile"]["employee_id"] == payload["employee_id"].upper()
    assert me["profile"]["hospital_name"] == "District Hospital Guntur"  # whitespace normalised


def test_admin_registration_requires_employee_id_and_hospital(client):
    res, _ = register_admin(client, employee_id="")
    assert res.status_code == 422
    res, _ = register_admin(client, hospital_name="")
    assert res.status_code == 422


def test_pending_admin_has_no_admin_powers(client, patient):
    _, payload = register_admin(client)
    h = login(client, payload["email"])
    assert client.get(f"{API}/admin/stats", headers=h).status_code == 403
    assert client.get(f"{API}/admin/users", headers=h).status_code == 403
    assert client.get(f"{API}/admin/audit-logs", headers=h).status_code == 403
    assert client.post(f"{API}/admin/content", headers=h, json={
        "title": "Unapproved", "body": "Should be blocked for pending admins", "category": "GENERAL_HEALTH",
    }).status_code == 403
    assert client.get(f"{API}/patients/{patient['patient_id']}/records", headers=h).status_code == 403


def test_verified_admin_approves_new_admin(client, admin):
    _, payload = register_admin(client)
    h = login(client, payload["email"])
    stats = client.get(f"{API}/admin/stats", headers=admin["headers"]).json()
    assert stats["pending_admin_verifications"] == 1

    pending = client.get(f"{API}/admin/users?verification_status=PENDING", headers=admin["headers"]).json()
    assert len(pending) == 1
    profile_id = pending[0]["admin_profile"]["id"]

    res = client.patch(f"{API}/admin/admins/{profile_id}/verification", headers=admin["headers"],
                       json={"verification_status": "VERIFIED"})
    assert res.status_code == 200 and res.json()["is_verified"] is True
    assert client.get(f"{API}/admin/stats", headers=h).status_code == 200
    assert client.get(f"{API}/admin/me", headers=h).json()["verification_status"] == "VERIFIED"


def test_rejected_admin_stays_blocked(client, admin):
    _, payload = register_admin(client)
    h = login(client, payload["email"])
    pid = client.get(f"{API}/admin/me", headers=h).json()["profile"]["id"]
    client.patch(f"{API}/admin/admins/{pid}/verification", headers=admin["headers"],
                 json={"verification_status": "REJECTED"})
    assert client.get(f"{API}/admin/stats", headers=h).status_code == 403
    assert client.get(f"{API}/admin/me", headers=h).json()["verification_status"] == "REJECTED"


def test_admin_cannot_verify_self(client, admin):
    # Approve a new admin, then try to have them change their own status.
    _, payload = register_admin(client)
    h = login(client, payload["email"])
    pid = client.get(f"{API}/admin/me", headers=h).json()["profile"]["id"]
    client.patch(f"{API}/admin/admins/{pid}/verification", headers=admin["headers"],
                 json={"verification_status": "VERIFIED"})
    res = client.patch(f"{API}/admin/admins/{pid}/verification", headers=h, json={"verification_status": "REJECTED"})
    assert res.status_code == 400


def test_duplicate_employee_id_same_hospital_rejected(client):
    _, first = register_admin(client, employee_id="EMP001", hospital_name="PHC Tenali")
    res, _ = register_admin(client, employee_id="emp001", hospital_name="phc tenali")
    assert res.status_code == 409
    other_hospital, _ = register_admin(client, employee_id="EMP001", hospital_name="PHC Guntur")
    assert other_hospital.status_code == 201


def test_other_roles_cannot_approve_admins(client, patient, worker):
    _, payload = register_admin(client)
    pid = client.get(f"{API}/admin/me", headers=login(client, payload["email"])).json()["profile"]["id"]
    for h in (patient["headers"], worker["headers"]):
        res = client.patch(f"{API}/admin/admins/{pid}/verification", headers=h, json={"verification_status": "VERIFIED"})
        assert res.status_code == 403
