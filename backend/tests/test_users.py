from tests.conftest import API


def test_retrieve_own_profile(client, patient):
    res = client.get(f"{API}/users/me", headers=patient["headers"])
    assert res.status_code == 200
    assert res.json()["email"] == patient["payload"]["email"]
    assert "password_hash" not in res.json()
    prof = client.get(f"{API}/patients/me", headers=patient["headers"])
    assert prof.status_code == 200
    assert prof.json()["profile"]["id"] == patient["patient_id"]


def test_update_profile(client, patient):
    res = client.patch(f"{API}/users/me", headers=patient["headers"],
                       json={"full_name": "Updated Name", "phone": "+91 99999 11111"})
    assert res.status_code == 200
    assert res.json()["full_name"] == "Updated Name"
    assert res.json()["phone"] == "+919999911111"
    assert res.json()["phone_verified"] is False  # a changed number must be verified again

    res = client.patch(f"{API}/patients/me", headers=patient["headers"],
                       json={"gender": "Female", "address": "Village Road", "date_of_birth": "1990-05-01",
                             "emergency_contact_name": "Relative", "emergency_contact_phone": "9123456780"})
    assert res.status_code == 200
    assert res.json()["profile"]["gender"] == "Female"


def test_update_profile_duplicate_email_rejected(client, patient, other_patient):
    res = client.patch(f"{API}/users/me", headers=patient["headers"],
                       json={"email": other_patient["payload"]["email"]})
    assert res.status_code == 409


def test_cannot_remove_all_contact_methods(client, patient):
    res = client.patch(f"{API}/users/me", headers=patient["headers"], json={"email": None, "phone": None})
    assert res.status_code == 422


def test_cannot_remove_phone(client, patient):
    res = client.patch(f"{API}/users/me", headers=patient["headers"], json={"phone": None})
    assert res.status_code == 422
    assert client.patch(f"{API}/users/me", headers=patient["headers"], json={"email": None}).status_code == 200


def test_update_language_preference(client, patient):
    res = client.patch(f"{API}/users/me/language", headers=patient["headers"], json={"preferred_language": "ta"})
    assert res.status_code == 200
    assert res.json()["preferred_language"] == "ta"
    bad = client.patch(f"{API}/users/me/language", headers=patient["headers"], json={"preferred_language": "xx"})
    assert bad.status_code == 422


def test_supported_languages_listed(client):
    res = client.get(f"{API}/languages")
    codes = {lang["code"] for lang in res.json()}
    assert codes == {"en", "te", "hi", "ta", "kn", "ml"}


def test_prevent_unauthorized_role_changes(client, patient):
    for field, value in (("role", "ADMIN"), ("is_verified", True), ("is_active", True)):
        res = client.patch(f"{API}/users/me", headers=patient["headers"], json={field: value})
        assert res.status_code == 422, field
    assert client.get(f"{API}/users/me", headers=patient["headers"]).json()["role"] == "PATIENT"


def test_patient_cannot_use_worker_profile_endpoint(client, patient):
    assert client.get(f"{API}/healthcare-workers/me", headers=patient["headers"]).status_code == 403


def test_worker_profile(client, worker):
    res = client.get(f"{API}/healthcare-workers/me", headers=worker["headers"])
    assert res.status_code == 200
    assert res.json()["profile"]["verification_status"] == "VERIFIED"
    assert client.get(f"{API}/patients/me", headers=worker["headers"]).status_code == 403
