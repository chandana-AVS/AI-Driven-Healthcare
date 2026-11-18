# API Documentation — Milestone 1

- Base URL: `http://localhost:8000/api/v1`
- Interactive docs: `http://localhost:8000/docs` (Swagger) · `/redoc`
- Machine-readable spec: [`openapi.json`](openapi.json) (also importable into Postman)
- Auth: `Authorization: Bearer <access_token>` on every endpoint except registration, login, `/languages`,
  `/content*` and `/health`.

## Error format

| Status | Meaning |
|---|---|
| 401 | Missing, invalid or expired token (`"Token has expired"`) or bad login credentials |
| 403 | Authenticated but not permitted (wrong role, unverified worker, no access grant, deactivated) |
| 404 | Not found, or not visible to you |
| 409 | Duplicate email/phone, or duplicate active grant |
| 429 | SMS code requested too often (`Retry-After` header gives the wait in seconds) |
| 503 | The SMS provider could not send the code |
| 413 | Upload exceeds the size limit |
| 415 | Unsupported or mismatched file type |
| 422 | Validation failed: `{"detail":"Validation failed","errors":[{"field":"password","message":"…"}]}` |

---

## Authentication

### POST /auth/register/patient → 201
```json
{ "full_name": "Sample Patient", "email": "patient@example.com", "phone": "9876543210",
  "password": "SecurePassword123", "preferred_language": "te" }
```
Rules: **phone is required**, email is optional. Password needs at least 8 characters, including a letter and a number.
Language must be one of `en te hi ta kn ml`. Unknown fields such as `role` are rejected.

### POST /auth/register/healthcare-worker → 201
Same body as the patient endpoint, plus `designation` and `organization`. New workers start as
`verification_status: PENDING`.

### POST /auth/register/admin → 201
Same body as the patient endpoint, plus `employee_id` and `hospital_name`. The account is created with
`is_verified: false` and `verification_status: PENDING`. Every admin endpoint returns **403** for it until a
verified admin calls `PATCH /admin/admins/{admin_profile_id}/verification`. An employee ID can be registered only
once per hospital (**409**). The pending admin can check their status with `GET /admin/me`.

### Phone verification (SMS)
Every registration sends a 6-digit code by SMS, and the account **cannot log in until the phone is verified**.
Login with a correct password on an unverified account returns **403** `{"detail":"Phone number not verified"}`
and sends a fresh code.

| Method | Path | Body | Result |
|---|---|---|---|
| POST | /auth/phone/verify | `{ "identifier": "9876543210", "code": "123456" }` | 200 `{"detail":"Phone number verified","phone_verified":true}` · 400 wrong or expired code |
| POST | /auth/phone/send-otp | `{ "identifier": "9876543210" }` | 202 (same reply whether or not the account exists) · 429 cooldown or hourly limit |

`identifier` can be the phone number or the email. Codes expire after 5 minutes and allow 5 wrong attempts.
Only the newest code is valid. Resending is allowed every 60 seconds, up to 5 codes per hour. Only an HMAC-SHA256
of the code is stored. Changing the phone number via `PATCH /users/me` sets `phone_verified=false` and sends a code
to the new number.

### POST /auth/login → 200
```json
{ "identifier": "patient@example.com", "password": "SecurePassword123" }
```
`identifier` accepts an email address or a phone number.
```json
{ "access_token": "eyJ…", "token_type": "bearer", "expires_in": 1800,
  "user": { "id": "…", "full_name": "Sample Patient", "role": "PATIENT", "preferred_language": "te" } }
```

## Users and profiles

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | /languages | public | Supported languages `[{code,name,native}]` |
| GET | /users/me | any | Current account |
| PATCH | /users/me | any | Update `full_name`, `email`, `phone`, `preferred_language`. `role` and `is_*` are rejected. The phone cannot be removed, and a new phone must be re-verified by SMS. |
| PATCH | /users/me/language | any | `{ "preferred_language": "hi" }` |
| GET / PATCH | /patients/me | patient | `{user, profile}`. Profile fields: date_of_birth, gender, address, emergency_contact_name/phone |
| GET / PATCH | /healthcare-workers/me | worker | `{user, profile}`. Profile fields: designation, organization |
| GET | /healthcare-workers/me/patients | verified worker | Patients who granted access, with document and record counts |

## Medical documents

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | /patients/me/documents | patient | Upload (multipart) |
| GET | /patients/me/documents?document_type= | patient | List own documents `{items,total}` |
| POST | /patients/{patient_id}/documents | authorized | Upload for a patient |
| GET | /patients/{patient_id}/documents | authorized | List a patient's documents |
| GET | /documents/{id} | authorized | Metadata |
| GET | /documents/{id}/download | authorized | File stream (`attachment`) |
| DELETE | /documents/{id} | owner patient, or the worker who uploaded it | 204 |

Multipart fields: `file` (PDF/JPG/JPEG/PNG, ≤ 10 MB) and `document_type` (PRESCRIPTION | DISCHARGE_SUMMARY |
DIAGNOSTIC_REPORT | LAB_REPORT | OTHER) are required. `document_date` (YYYY-MM-DD) and `document_name` are
optional.

```bash
curl -X POST http://localhost:8000/api/v1/patients/me/documents \
  -H "Authorization: Bearer $TOKEN" -F "file=@prescription.pdf" -F "document_type=PRESCRIPTION"
```

## Healthcare records and history

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | /patients/me/records | patient | Own records, newest `record_date` first |
| GET | /patients/me/history | patient | Combined timeline of records and documents |
| POST | /patients/{patient_id}/records | authorized | Create record |
| GET | /patients/{patient_id}/records | authorized | List records |
| GET | /patients/{patient_id}/history | authorized | Timeline |
| GET | /records/{id} | authorized | Single record |

```json
{ "record_type": "CONSULTATION", "title": "BP check", "description": "120/80",
  "record_date": "2026-11-10", "document_id": null }
```
`record_date` cannot be in the future. `document_id` must belong to the same patient.

History entry: `{entry_type: "RECORD"|"DOCUMENT", date, timestamp, title, category, status, description, record?, document?}`.

## Access grants (patient-controlled)

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | /patients/me/workers?search= | patient | Directory of verified, active workers |
| GET | /patients/me/access | patient | Own grants (active and revoked) |
| POST | /patients/me/access | patient | `{ "healthcare_worker_id": "…" }` or `{ "worker_identifier": "worker@example.com" }` |
| DELETE | /patients/me/access/{grant_id} | patient | Revoke |

## Healthcare content

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | /content?category=&language=&search= | public | Published content only |
| GET | /content/categories | public | Category list |
| GET | /content/{id} | public | Published item |
| GET | /admin/content?status= | admin | All content |
| POST | /admin/content | admin | `{title, body, category, language_code, status}` (status defaults to DRAFT) |
| PATCH | /admin/content/{id} | admin | Partial update, including publish (`PUBLISHED`) or deactivate (`INACTIVE`) |
| DELETE | /admin/content/{id} | admin | 204 |

## Administration

| Method | Path | Purpose |
|---|---|---|
| GET | /admin/me | Own approval status (works for pending admins too) |
| PATCH | /admin/admins/{admin_profile_id}/verification | Approve or reject a self-registered admin `{ "verification_status": "VERIFIED" }`. You cannot change your own status. |
| GET | /admin/stats | Patients, workers, pending worker and admin verifications, documents, grants, content counts |
| GET | /admin/users?role=&verification_status=&search= | User list (with worker profile) |
| PATCH | /admin/users/{user_id}/status | `{ "is_active": false }` |
| PATCH | /admin/healthcare-workers/{worker_id}/verification | `{ "verification_status": "VERIFIED" }` |
| GET / POST | /admin/access | List or create grants `{patient_id, healthcare_worker_id}` |
| DELETE | /admin/access/{grant_id} | Revoke |
| GET | /admin/audit-logs?limit=&action= | Audit trail |

## Health

`GET /health` → `{"status":"ok","database":"connected"}`
