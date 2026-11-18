from app.config import settings
from tests.conftest import API, JPG_BYTES, PDF_BYTES, PNG_BYTES, grant, upload


def test_upload_pdf(client, patient):
    res = upload(client, patient["headers"], document_date="2026-11-01")
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["document_type"] == "PRESCRIPTION"
    assert body["mime_type"] == "application/pdf"
    assert body["processing_status"] == "UPLOADED"
    assert body["file_size"] == len(PDF_BYTES)
    assert "storage_key" not in body  # private path never exposed


def test_upload_images(client, patient):
    png = upload(client, patient["headers"], name="scan.png", content=PNG_BYTES, mime="image/png",
                 document_type="LAB_REPORT")
    jpg = upload(client, patient["headers"], name="report.JPEG", content=JPG_BYTES, mime="image/jpeg",
                 document_type="DIAGNOSTIC_REPORT")
    assert png.status_code == 201 and jpg.status_code == 201
    assert jpg.json()["mime_type"] == "image/jpeg"


def test_reject_unsupported_file(client, patient):
    res = upload(client, patient["headers"], name="malware.exe", content=b"MZ\x90\x00", mime="application/octet-stream")
    assert res.status_code == 415
    # Correct extension but fake content
    fake = upload(client, patient["headers"], name="fake.pdf", content=b"<html>not a pdf</html>")
    assert fake.status_code == 415
    # Extension / declared MIME mismatch
    mismatch = upload(client, patient["headers"], name="x.pdf", content=PDF_BYTES, mime="text/html")
    assert mismatch.status_code == 415


def test_reject_invalid_document_type(client, patient):
    res = upload(client, patient["headers"], document_type="SELFIE")
    assert res.status_code == 422


def test_reject_oversized_file(client, patient):
    big = PDF_BYTES + b"0" * (settings.max_upload_bytes + 1)
    res = upload(client, patient["headers"], content=big)
    assert res.status_code == 413


def test_reject_empty_file(client, patient):
    res = upload(client, patient["headers"], content=b"")
    assert res.status_code in (400, 415)


def test_path_traversal_filename_is_neutralised(client, patient):
    res = upload(client, patient["headers"], name="../../../../etc/passwd.pdf")
    assert res.status_code == 201
    assert res.json()["document_name"] == "passwd.pdf"


def test_list_and_retrieve_metadata(client, patient):
    doc = upload(client, patient["headers"]).json()
    upload(client, patient["headers"], document_type="DISCHARGE_SUMMARY")
    listing = client.get(f"{API}/patients/me/documents", headers=patient["headers"]).json()
    assert listing["total"] == 2
    filtered = client.get(f"{API}/patients/me/documents?document_type=DISCHARGE_SUMMARY",
                          headers=patient["headers"]).json()
    assert filtered["total"] == 1
    meta = client.get(f"{API}/documents/{doc['id']}", headers=patient["headers"])
    assert meta.status_code == 200 and meta.json()["id"] == doc["id"]


def test_download_authorized_document(client, patient):
    doc = upload(client, patient["headers"]).json()
    res = client.get(f"{API}/documents/{doc['id']}/download", headers=patient["headers"])
    assert res.status_code == 200
    assert res.content == PDF_BYTES
    assert res.headers["content-type"].startswith("application/pdf")
    assert "attachment" in res.headers["content-disposition"]


def test_reject_unauthorized_document_access(client, patient, other_patient, worker):
    doc = upload(client, patient["headers"]).json()
    for headers in (other_patient["headers"], worker["headers"]):
        assert client.get(f"{API}/documents/{doc['id']}", headers=headers).status_code == 404
        assert client.get(f"{API}/documents/{doc['id']}/download", headers=headers).status_code == 404
        assert client.delete(f"{API}/documents/{doc['id']}", headers=headers).status_code == 404
    assert client.get(f"{API}/documents/{doc['id']}").status_code == 401


def test_delete_document(client, patient):
    doc = upload(client, patient["headers"]).json()
    assert client.delete(f"{API}/documents/{doc['id']}", headers=patient["headers"]).status_code == 204
    assert client.get(f"{API}/documents/{doc['id']}", headers=patient["headers"]).status_code == 404


def test_authorized_worker_document_access(client, patient, worker):
    doc = upload(client, patient["headers"]).json()
    grant(client, patient, worker)
    url = f"{API}/patients/{patient['patient_id']}/documents"
    assert client.get(url, headers=worker["headers"]).json()["total"] == 1
    assert client.get(f"{API}/documents/{doc['id']}/download", headers=worker["headers"]).status_code == 200

    uploaded = upload(client, worker["headers"], url=url, document_type="LAB_REPORT")
    assert uploaded.status_code == 201
    # Worker may delete what they uploaded, but not the patient's own uploads.
    assert client.delete(f"{API}/documents/{doc['id']}", headers=worker["headers"]).status_code == 403
    assert client.delete(f"{API}/documents/{uploaded.json()['id']}", headers=worker["headers"]).status_code == 204


def test_worker_loses_access_after_revocation(client, patient, worker):
    doc = upload(client, patient["headers"]).json()
    g = grant(client, patient, worker)
    assert client.get(f"{API}/documents/{doc['id']}", headers=worker["headers"]).status_code == 200
    res = client.delete(f"{API}/patients/me/access/{g['id']}", headers=patient["headers"])
    assert res.status_code == 200 and res.json()["access_status"] == "REVOKED"
    assert client.get(f"{API}/documents/{doc['id']}", headers=worker["headers"]).status_code == 404
    assert client.get(f"{API}/patients/{patient['patient_id']}/documents",
                      headers=worker["headers"]).status_code == 403
