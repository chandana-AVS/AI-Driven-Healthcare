# AI-Driven Healthcare Assistance Platform — Milestones 1 & 2

Patient & Healthcare Information Management System for rural communities, with multilingual support built in
from day one. Milestone 1 delivers the secure data and application foundation: accounts, roles, profiles,
language preferences, medical-document storage, patient history, access control and a healthcare content
repository.

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite 6 + Tailwind CSS 4, Axios, React Router, lucide-react |
| Backend | Python 3.11 + FastAPI, SQLAlchemy 2, Alembic, Pydantic 2 |
| Database | PostgreSQL (SQLite is used only for the automated tests) |
| Auth | JWT (HS256) access tokens, Argon2 password hashing |
| Storage | Private local filesystem (`backend/storage/medical_documents`), swappable for cloud object storage |

```
backend/    FastAPI app, models, routers, services, Alembic migrations, tests, scripts
frontend/   React app (pages, components, AuthContext, api service)
docs/       Requirements, architecture, database design, API docs, openapi.json
```

---

## 1. Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 14+ (running locally on port 5432)

## 2. Database

Create the database (psql or pgAdmin):

```sql
CREATE DATABASE healthcare_assistant;
```

## 3. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env        # then edit .env (see below)
alembic upgrade head          # create all tables
python -m scripts.create_admin --email admin@example.com --name "System Admin"   # prompts for a password
python -m scripts.seed_content   # optional: sample education content (inserted as DRAFT)

uvicorn app.main:app --reload
```

`.env` settings:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:<password>@localhost:5432/healthcare_assistant` |
| `JWT_SECRET_KEY` | Long random secret — generate with `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (default 30) |
| `MAX_UPLOAD_SIZE_MB` | Upload limit (default 10) |
| `STORAGE_PATH` | Private document directory (default `storage/medical_documents`) |
| `CORS_ORIGINS` | Comma-separated frontend origins (default Vite dev server) |
| `SMS_PROVIDER` | `console` (default): verification codes are printed in the **backend terminal**. `twilio`: real SMS, needs `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` |
| `SMS_DEFAULT_COUNTRY_CODE` | Added to numbers entered without `+` (default `+91`) |

- Swagger UI: http://127.0.0.1:8000/docs (click **Authorize** and paste an `access_token` from `/auth/login`)
- Health check: http://127.0.0.1:8000/health

## 4. Frontend

```powershell
cd frontend
npm install
copy .env.example .env        # VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev                   # http://localhost:5173
```

## 5. Tests

```powershell
cd backend
.\venv\Scripts\python -m pytest
```

There are 69 tests covering authentication, SMS phone verification, profile management, document management, patient history, access
control, admin and content. They run against an isolated temporary SQLite database and storage folder, so they
never touch your PostgreSQL data.

## 6. Postman

Import `docs/openapi.json` into Postman (**Import → File**). This creates a collection with every endpoint.
Set a `bearer` token in the collection's **Authorization** tab after logging in.

## 7. Docker (deployment preparation)

```powershell
docker compose up --build     # PostgreSQL + backend on http://localhost:8000
```

The backend container runs `alembic upgrade head` automatically on start.

---

## Milestone 1 demonstration script

1. Open http://localhost:5173 and click **Register as Patient**. A phone number is required and email is optional. Choose **తెలుగు / हिन्दी** or another language. Enter the 6-digit SMS code. With `SMS_PROVIDER=console` it is printed in the backend terminal as `[DEV SMS] to +91…: 123456 is your…`.
2. Log in as the patient to reach the **Patient Dashboard**.
3. Upload a sample prescription (PDF/JPG/PNG). It appears under **Recent documents**, **Documents** and **Medical History**.
4. In a second browser (or a private window), register as a **Healthcare Worker**.
5. Log in as the admin. On **Overview → awaiting verification**, click **Verify** for the worker.
6. As the patient, open **Care Team** and click **Grant access** next to the worker.
7. As the worker, open **Dashboard**. The patient is listed. Open them to view history and documents, add a record and upload a document.
8. To show that unauthorized access is blocked: as the patient, click **Revoke**. The worker can no longer open the patient. You can also call `GET /api/v1/patients/{id}/records` with another patient's token in Swagger and get **403**.

## Roles and access rules

| Role | Can do |
|---|---|
| Patient | Manage own profile and language; upload, list, download and delete own documents; view own history; grant or revoke healthcare-worker access |
| Healthcare worker | Manage own profile. Once **verified by an admin**, and only for patients with an **active grant**: view history, records and documents; add records; upload documents; delete documents they uploaded |
| Admin | Registers on the Register page (**Admin** tab) with **Employee ID + Hospital name**. The account stays **PENDING**, with no admin permissions, until an existing verified admin approves it. The first admin is created with `scripts.create_admin`. Once approved: dashboard stats; activate or deactivate users; verify or reject workers; review and revoke access grants; create, edit, publish, deactivate and delete content; view the audit log. Admins cannot read patient medical data. |

## Out of scope for Milestone 1

OCR, medical NLP, AI translation, voice, reminders and mobile apps arrive in later milestones. The schema is
ready for them: original files are preserved, `processing_status` tracks a document's AI pipeline state, and
`preferred_language` / `language_code` use shared ISO codes.

**Milestone 2 (AI translation & simplification engine):** see [docs/MILESTONE_2.md](docs/MILESTONE_2.md). Add `OPENAI_API_KEY` to `backend/.env` to switch it on.

See [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md), [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md)
and [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md).
