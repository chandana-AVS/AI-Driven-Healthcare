# System Architecture — Milestone 1

## 1. Overview

The application has three tiers plus a private file store.

```text
 Patient / Healthcare Worker / Admin  (browser)
                 │
        React + Vite SPA  (frontend/)
   AuthContext · ProtectedRoute · services/api.js (Axios)
                 │  REST/JSON + multipart, Authorization: Bearer <JWT>
        FastAPI  (backend/app)
   routers/  ──►  dependencies.py (auth, roles)  ──►  services/
                                                    ├─ auth_service      registration, login
                                                    ├─ user_service      profile, language
                                                    ├─ access_service    ★ all patient-data authorization
                                                    ├─ document_service  upload/list/delete
                                                    ├─ record_service    records + chronological history
                                                    ├─ storage_service   private file storage (pluggable)
                                                    └─ audit_service     audit log
                 │ SQLAlchemy 2                              │ filesystem
           PostgreSQL                              storage/medical_documents/
   users · patient_profiles · healthcare_worker_profiles        patient_<uuid>/<random>.pdf
   medical_documents · healthcare_records · healthcare_content
   patient_access · audit_logs
```

## 2. Backend layering

| Layer | Folder | Responsibility |
|---|---|---|
| Routers | `app/routers` | HTTP shape: paths, status codes, request/response models |
| Dependencies | `app/dependencies.py` | Decode JWT → `User`, role guards (`require_roles`, `require_admin`), `get_current_patient`, `get_verified_worker` |
| Services | `app/services` | Business rules and authorization. Routers stay thin. |
| Schemas | `app/schemas` | Pydantic request validation and response models. Responses never include `password_hash` or `storage_key`. |
| Models | `app/models` | SQLAlchemy ORM tables, constraints and indexes |
| Utils | `app/utils` | Argon2 + JWT (`security.py`), field validators, upload validation (`file_handler.py`) |

## 3. Authorization model

`access_service.authorize_patient_access(db, user, patient_id)` is the single gate for every patient-specific
operation:

| Caller | Allowed when |
|---|---|
| PATIENT | `patient_id` is their own profile |
| HEALTHCARE_WORKER | profile `verification_status = VERIFIED` **and** an `ACTIVE` row exists in `patient_access` |
| ADMIN | never. Admins manage users, grants and content, not medical data. |

- Grants are created by the patient (`POST /patients/me/access`) or by an admin. They are revoked by setting
  `access_status = REVOKED` and `revoked_at`, so history is kept. A partial unique index allows only one ACTIVE
  grant per patient/worker pair.
- Unauthorized calls to `/documents/{id}` and `/records/{id}` return **404**, so the API does not reveal whether a
  resource exists. Unauthorized calls to `/patients/{id}/…` return **403**.
- Deactivated accounts are rejected at login and on every authenticated request.

## 4. Authentication

- Passwords are hashed with Argon2id (`argon2-cffi`). Login runs a dummy hash check for unknown users to equalise
  timing, and returns one generic message for any failure.
- Access tokens are JWT HS256 with `sub`, `role`, `iat`, `exp` and `type=access`. They expire after 30 minutes
  (configurable).
- Frontend: the token is held in memory and mirrored to `sessionStorage`, which is cleared when the tab closes.
  It is never stored in `localStorage`. A 401 response clears the session and sends the user to login.
  **Production:** move to an HttpOnly, Secure, SameSite cookie with a refresh-token rotation endpoint.

## 5. Document storage and upload security

1. The extension must be in an allowlist: `.pdf .jpg .jpeg .png`.
2. The declared MIME type must match the extension.
3. Magic bytes must match a PDF, JPEG or PNG signature, so the browser's claim is not trusted.
4. The file is read in chunks and rejected with **413** once it passes `MAX_UPLOAD_SIZE_MB`.
5. The server generates the filename: `patient_<uuid>/<uuid4>.<ext>`. The client's filename is only display
   metadata and is stripped of path components.
6. `LocalStorage._resolve` checks that every path stays inside the storage root (path-traversal guard).
7. Files are written atomically (`.part` file, then rename). If the DB commit fails, the file is removed.
8. Downloads stream through an authorized endpoint with `Content-Disposition: attachment`, `Cache-Control: no-store`
   and `nosniff`. Storage paths are never exposed.

`storage_service` exposes only `save / open_path / delete`, so it can be swapped for private S3/GCS/Azure Blob
storage without touching callers.

## 6. Audit logging

`audit_logs` records registration, login (including failures), document upload/list/view/download/delete, record
create/list/view, history views, access grant/revoke, user activation, worker verification and content changes.
Only identifiers are stored (actor, resource, patient, IP), never medical content. Admins can view the log in the
dashboard.

## 7. Error handling

- Validation errors return 422 as `{"detail": "Validation failed", "errors": [{field, message}]}`. Submitted
  values are not echoed back.
- Unhandled exceptions are logged server-side and return a generic `500 Internal server error`.
- Security headers on every response: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`.

## 8. Readiness for later milestones

| Future module | Hook already in place |
|---|---|
| OCR / NLP / translation (M2) | Original files preserved; `medical_documents.processing_status` (UPLOADED → QUEUED → PROCESSING → PROCESSED/FAILED); storage abstraction |
| Translation / voice (M2–M3) | `users.preferred_language`, `healthcare_content.language_code`, shared `LanguageCode` enum and `GET /languages` |
| Medication reminders (M3) | `healthcare_records.record_type` is open-ended VARCHAR; new tables can attach to `patient_profiles.id` |
| Mobile apps (M4) | Stateless REST + bearer tokens, CORS-configurable |
| Deployment (M5) | Dockerfile, docker-compose, env-based config, Alembic migrations |
