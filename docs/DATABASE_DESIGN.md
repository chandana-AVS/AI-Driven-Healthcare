# Database Design — Milestone 1

Database: **PostgreSQL** `healthcare_assistant`. The schema is managed by Alembic
(`backend/alembic/versions/0001_initial_schema.py`). All primary keys are UUIDs and all timestamps are
timezone-aware (UTC). Enumerated values are stored as `VARCHAR`, with CHECK constraints where the set is fixed,
so later milestones can add values without enum migrations.

## Entity relationships

```text
users 1───1 patient_profiles 1───* medical_documents *───1 users (uploaded_by)
  │                 │      └────* healthcare_records *───1 users (created_by)
  │                 │                    └── document_id ──► medical_documents (nullable)
  │                 └────* patient_access *───1 healthcare_worker_profiles
  └──1 healthcare_worker_profiles                     └── granted_by ──► users
users 1───* healthcare_content (created_by)
users 1───* audit_logs (actor_id)
```

## Tables

### users
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| full_name | VARCHAR(150) NOT NULL | |
| email | VARCHAR(255) UNIQUE | lower-cased |
| phone | VARCHAR(20) UNIQUE | normalised digits, optional leading `+` |
| password_hash | TEXT NOT NULL | Argon2id |
| role | VARCHAR(30) NOT NULL | CHECK in (PATIENT, HEALTHCARE_WORKER, ADMIN); indexed |
| preferred_language | VARCHAR(10) NOT NULL | en, te, hi, ta, kn, ml |
| is_active | BOOLEAN NOT NULL | |
| is_verified | BOOLEAN NOT NULL | true for verified workers and admins |
| phone_verified | BOOLEAN NOT NULL | set by SMS code; login is blocked while false (migration 0003) |
| created_at / updated_at | TIMESTAMPTZ | |

`CHECK (email IS NOT NULL OR phone IS NOT NULL)`

### patient_profiles
`id` PK · `user_id` FK→users **UNIQUE, ON DELETE CASCADE** · date_of_birth · gender · address ·
emergency_contact_name · emergency_contact_phone · created_at

### healthcare_worker_profiles
`id` PK · `user_id` FK→users **UNIQUE, ON DELETE CASCADE** · designation · organization ·
`verification_status` (CHECK PENDING/VERIFIED/REJECTED, indexed) · created_at

### admin_profiles (migration 0002)
`id` PK · `user_id` FK→users **UNIQUE, ON DELETE CASCADE** · employee_id (stored upper-case) · hospital_name ·
`verification_status` (CHECK PENDING/VERIFIED/REJECTED, indexed) · created_at.
`UNIQUE (hospital_name, employee_id)`. An admin acts as an admin only when `users.is_verified = true`.

### phone_otps (migration 0003)
`id` PK · `user_id` FK→users (CASCADE) · phone (number the code was sent to) · code_hash (HMAC-SHA256, never the
code) · expires_at · attempts · consumed_at · created_at. Index `(user_id, created_at)`.

### medical_documents
| Column | Notes |
|---|---|
| patient_id | FK→patient_profiles, ON DELETE CASCADE |
| uploaded_by | FK→users, ON DELETE SET NULL |
| document_name | display name only (never used as a path) |
| document_type | PRESCRIPTION, DISCHARGE_SUMMARY, DIAGNOSTIC_REPORT, LAB_REPORT, OTHER (indexed) |
| storage_key | UNIQUE, private relative path; never returned by the API |
| mime_type, file_size (BIGINT), document_date | |
| processing_status | UPLOADED (M1) → QUEUED/PROCESSING/PROCESSED/FAILED (M2+) |

Index: `(patient_id, created_at)`

### healthcare_records
patient_id FK (CASCADE) · created_by FK→users (SET NULL) · record_type · title · description · record_date ·
document_id FK→medical_documents (SET NULL, nullable) · created_at. Index: `(patient_id, record_date)`.

Record types: CONSULTATION, DIAGNOSIS, PRESCRIPTION, DISCHARGE, LAB_RESULT, IMMUNIZATION, DOCUMENT_UPLOAD, NOTE, OTHER.

### healthcare_content
title · body · category (GENERAL_HEALTH, MATERNAL_HEALTH, CHILD_HEALTHCARE, ELDERLY_CARE, PREVENTIVE_HEALTHCARE,
COMMON_DISEASES) · language_code · status (DRAFT, PUBLISHED, INACTIVE) · created_by FK→users (SET NULL) ·
created_at · updated_at. Index: `(status, language_code, category)`.

### patient_access
patient_id FK (CASCADE) · healthcare_worker_id FK→healthcare_worker_profiles (CASCADE) · access_status
(ACTIVE/REVOKED) · granted_by FK→users (SET NULL) · created_at · revoked_at.

**Partial unique index** `uq_patient_access_active (patient_id, healthcare_worker_id) WHERE access_status = 'ACTIVE'`
allows only one active grant per pair while keeping revoked rows as history.

### audit_logs (added for security requirement 12)
actor_id FK→users (SET NULL) · action · resource_type · resource_id · patient_id · ip_address · details ·
created_at. Contains identifiers only, never medical content.

## Deletion rules

- Deleting a user cascades to that user's profile. A patient profile then cascades to its documents, records and
  access grants.
- References to users who authored rows (`uploaded_by`, `created_by`, `granted_by`, `actor_id`) are SET NULL, so
  clinical history and audit trails survive.
- Deleting a document SET NULLs `healthcare_records.document_id`. The record stays and the file is removed from
  storage.

## Migrations

```powershell
alembic upgrade head                                    # apply
alembic downgrade base                                  # roll back everything
alembic revision --autogenerate -m "describe change"    # after editing models
```
