from datetime import date, timedelta

from tests.conftest import API, grant, upload


def _record(title, days_ago, **extra):
    return {"record_type": "CONSULTATION", "title": title,
            "description": "Routine visit", "record_date": str(date.today() - timedelta(days=days_ago)), **extra}


# ----------------------------------------------------------------------------- patient history
def test_create_healthcare_record(client, patient, worker):
    grant(client, patient, worker)
    doc = upload(client, patient["headers"]).json()
    res = client.post(f"{API}/patients/{patient['patient_id']}/records", headers=worker["headers"],
                      json=_record("BP check", 1, document_id=doc["id"]))
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["created_by_name"] == worker["payload"]["full_name"]
    assert body["document_id"] == doc["id"]


def test_record_cannot_link_other_patients_document(client, patient, other_patient, worker):
    grant(client, patient, worker)
    foreign_doc = upload(client, other_patient["headers"]).json()
    res = client.post(f"{API}/patients/{patient['patient_id']}/records", headers=worker["headers"],
                      json=_record("Bad link", 1, document_id=foreign_doc["id"]))
    assert res.status_code == 422


def test_retrieve_patient_records_chronological(client, patient, worker):
    grant(client, patient, worker)
    url = f"{API}/patients/{patient['patient_id']}/records"
    for title, days in (("Oldest", 30), ("Newest", 0), ("Middle", 10)):
        assert client.post(url, headers=worker["headers"], json=_record(title, days)).status_code == 201
    titles = [r["title"] for r in client.get(f"{API}/patients/me/records", headers=patient["headers"]).json()]
    assert titles == ["Newest", "Middle", "Oldest"]
    assert [r["title"] for r in client.get(url, headers=worker["headers"]).json()] == titles


def test_history_merges_documents_and_records(client, patient, worker):
    grant(client, patient, worker)
    upload(client, patient["headers"], document_date=str(date.today() - timedelta(days=5)))
    client.post(f"{API}/patients/{patient['patient_id']}/records", headers=worker["headers"],
                json=_record("Follow-up", 1))
    history = client.get(f"{API}/patients/me/history", headers=patient["headers"]).json()
    assert [e["entry_type"] for e in history["entries"]] == ["RECORD", "DOCUMENT"]
    assert history["entries"][1]["status"] == "UPLOADED"


def test_record_future_date_rejected(client, patient):
    res = client.post(f"{API}/patients/{patient['patient_id']}/records", headers=patient["headers"],
                      json=_record("Future", -5))
    assert res.status_code == 422


# ----------------------------------------------------------------------------- security
def test_prevent_cross_patient_access(client, patient, other_patient):
    pid = patient["patient_id"]
    h = other_patient["headers"]
    assert client.get(f"{API}/patients/{pid}/records", headers=h).status_code == 403
    assert client.post(f"{API}/patients/{pid}/records", headers=h, json=_record("Intrusion", 1)).status_code == 403
    assert client.get(f"{API}/patients/{pid}/documents", headers=h).status_code == 403
    assert client.get(f"{API}/patients/{pid}/history", headers=h).status_code == 403
    assert upload(client, h, url=f"{API}/patients/{pid}/documents").status_code == 403


def test_worker_without_permission_blocked(client, patient, worker):
    pid = patient["patient_id"]
    assert client.get(f"{API}/patients/{pid}/records", headers=worker["headers"]).status_code == 403
    assert client.get(f"{API}/patients/{pid}/documents", headers=worker["headers"]).status_code == 403
    assert client.get(f"{API}/healthcare-workers/me/patients", headers=worker["headers"]).json() == []


def test_unverified_worker_blocked(client, patient, unverified_worker):
    # Patients cannot grant access to unverified workers...
    res = client.post(f"{API}/patients/me/access", headers=patient["headers"],
                      json={"healthcare_worker_id": unverified_worker["worker_id"]})
    assert res.status_code == 400
    # ...and unverified workers cannot reach restricted endpoints.
    h = unverified_worker["headers"]
    assert client.get(f"{API}/healthcare-workers/me/patients", headers=h).status_code == 403
    assert client.get(f"{API}/patients/{patient['patient_id']}/records", headers=h).status_code == 403


def test_worker_access_after_grant_and_patient_list(client, patient, worker):
    grant(client, patient, worker)
    patients = client.get(f"{API}/healthcare-workers/me/patients", headers=worker["headers"]).json()
    assert len(patients) == 1 and patients[0]["patient_id"] == patient["patient_id"]
    assert client.get(f"{API}/patients/{patient['patient_id']}/history", headers=worker["headers"]).status_code == 200


def test_grant_by_identifier_and_duplicate(client, patient, worker):
    res = client.post(f"{API}/patients/me/access", headers=patient["headers"],
                      json={"worker_identifier": worker["payload"]["email"]})
    assert res.status_code == 201
    dup = client.post(f"{API}/patients/me/access", headers=patient["headers"],
                      json={"worker_identifier": worker["payload"]["email"]})
    assert dup.status_code == 409


def test_patient_cannot_revoke_others_grant(client, patient, other_patient, worker):
    g = grant(client, patient, worker)
    res = client.delete(f"{API}/patients/me/access/{g['id']}", headers=other_patient["headers"])
    assert res.status_code == 404


def test_admin_only_endpoints_reject_other_roles(client, patient, worker):
    for h in (patient["headers"], worker["headers"]):
        assert client.get(f"{API}/admin/stats", headers=h).status_code == 403
        assert client.get(f"{API}/admin/users", headers=h).status_code == 403
        assert client.post(f"{API}/admin/content", headers=h, json={
            "title": "Hack", "body": "Should not be allowed", "category": "GENERAL_HEALTH"}).status_code == 403
    assert client.get(f"{API}/admin/stats").status_code == 401


def test_admin_cannot_read_patient_medical_data(client, patient, admin):
    assert client.get(f"{API}/patients/{patient['patient_id']}/records", headers=admin["headers"]).status_code == 403


# ----------------------------------------------------------------------------- admin + content
def test_admin_verifies_worker_and_stats(client, admin, unverified_worker, patient):
    stats = client.get(f"{API}/admin/stats", headers=admin["headers"]).json()
    assert stats["pending_verifications"] == 1 and stats["total_patients"] == 1
    res = client.patch(f"{API}/admin/healthcare-workers/{unverified_worker['worker_id']}/verification",
                       headers=admin["headers"], json={"verification_status": "VERIFIED"})
    assert res.status_code == 200 and res.json()["is_verified"] is True
    assert client.get(f"{API}/healthcare-workers/me/patients", headers=unverified_worker["headers"]).status_code == 200
    pending = client.get(f"{API}/admin/users?verification_status=PENDING", headers=admin["headers"]).json()
    assert pending == []


def test_content_lifecycle(client, admin):
    payload = {"title": "Hand Washing", "body": "Wash hands with soap for 20 seconds.",
               "category": "GENERAL_HEALTH", "language_code": "te"}
    created = client.post(f"{API}/admin/content", headers=admin["headers"], json=payload)
    assert created.status_code == 201 and created.json()["status"] == "DRAFT"
    cid = created.json()["id"]

    assert client.get(f"{API}/content").json() == []           # drafts are not public
    assert client.get(f"{API}/content/{cid}").status_code == 404

    res = client.patch(f"{API}/admin/content/{cid}", headers=admin["headers"], json={"status": "PUBLISHED"})
    assert res.json()["status"] == "PUBLISHED"
    assert len(client.get(f"{API}/content?category=GENERAL_HEALTH&language=te").json()) == 1
    assert client.get(f"{API}/content?language=en").json() == []

    client.patch(f"{API}/admin/content/{cid}", headers=admin["headers"], json={"status": "INACTIVE"})
    assert client.get(f"{API}/content").json() == []

    assert client.delete(f"{API}/admin/content/{cid}", headers=admin["headers"]).status_code == 204
    assert client.get(f"{API}/admin/content", headers=admin["headers"]).json() == []


def test_audit_log_records_sensitive_access(client, admin, patient):
    doc = upload(client, patient["headers"]).json()
    client.get(f"{API}/documents/{doc['id']}/download", headers=patient["headers"])
    logs = client.get(f"{API}/admin/audit-logs", headers=admin["headers"]).json()
    actions = {entry["action"] for entry in logs}
    assert {"DOCUMENT_UPLOAD", "DOCUMENT_DOWNLOAD", "LOGIN", "REGISTER"} <= actions
