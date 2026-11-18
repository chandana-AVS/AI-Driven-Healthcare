# Milestone 2 — AI Medical Language Translation & Simplification Engine (Weeks 3–4)

Milestone 2 adds an AI engine on top of the Milestone 1 platform. It reads uploaded prescriptions and discharge
summaries and explains them in simple words in six languages (English, Telugu, Hindi, Tamil, Kannada and Malayalam).
It also extracts medicines and diseases, gives symptom-awareness guidance, and adds a multilingual knowledge base.

Text features use OpenAI **GPT-4o mini** (`gpt-4o-mini`); uploaded documents are read by **GPT-4o** (`gpt-4o`), which is
much better at handwriting. Both are called through the official `openai` Python SDK (Responses API) and read PDFs
and photos directly, so no separate OCR step is needed.

**Handwritten prescriptions.** Photos are rotated upright and contrast-enhanced (`app/utils/image_prep.py`). Tall
photos are sent as the full page plus overlapping zoomed-in strips at high detail, because the API shrinks a whole
page so far that small handwriting is lost. The prompt explains Indian prescription shorthand (1-0-1, T./Cap/Syp,
c/o, O/E, Adv, bracketed "after meals"), and every medicine carries a `confidence` level; anything not clearly
legible is shown with a "Please confirm with your pharmacist" badge.

**Saved translations.** Every document translation is stored per language. Document cards list the saved
languages, the explain page keeps the language in the URL (`?lang=te`) so Back and refresh reopen it, and
`GET /documents/{id}/analyses` lists them. Results can be copied, printed or read aloud. Assistant-page results
are kept for the browser tab and cleared on logout.

## Requirement coverage

| Requirement | Where it is implemented |
|---|---|
| Translate prescriptions, discharge summaries and healthcare instructions | `POST /ai/translate` (`text_type` = PRESCRIPTION / DISCHARGE_SUMMARY / INSTRUCTIONS / GENERAL); document translation in `POST /documents/{id}/analysis` |
| Support multiple Indian languages | `en te hi ta kn ml` on every AI endpoint |
| Convert medical terms into simple language; easy explanations | `POST /ai/simplify`; `summary`, `glossary` and simple `instructions` in every result |
| Context-based healthcare guidance | `guidance` and `questions_for_doctor` (simplify); `warning_signs` (documents) |
| Medical entity extraction: disease, medication, treatment instructions | `POST /ai/extract`, plus `entities` in document analysis (conditions, medications with dose/frequency/timing/duration, tests, instructions, symptoms, follow-up) |
| Symptom information retrieval | `POST /ai/symptoms`: urgency level, possible causes, self-care, when to see a doctor, emergency signs |
| Disease awareness and preventive care content | `prevention` in symptom guidance; DISEASE_INFO entries; related knowledge-base articles returned with symptom answers |
| Multilingual knowledge base: FAQs, common diseases, awareness content | `content_type` = FAQ / DISEASE_INFO / ARTICLE; `scripts.seed_knowledge_base`; AI translation `POST /admin/content/{id}/translate`; language switcher via `GET /content/{id}/translations` |

## How it works

1. **Document analysis.** A patient (or a worker with an active grant) clicks **Explain & translate** on a document
   and picks a language. The backend creates a `document_analyses` row (PENDING) and answers `202` at once. A
   background task sends the PDF or image to OpenAI and stores the structured result. The page polls until the
   status is COMPLETED, usually under a minute. One analysis is kept per document per language and is reused
   unless `force=true`.
2. **Structured output.** Every call uses `responses.parse` (structured outputs) with a Pydantic schema (`app/schemas/ai.py`), so the
   response is always valid JSON with the expected fields.
3. **Safety rules in the prompts** (`app/services/ai_service.py`):
   - Copy medicine names, doses and numbers exactly; never invent or change them.
   - List unreadable parts instead of guessing.
   - Never tell the patient to start, stop or change a medicine.
   - For symptoms, pick the more urgent level when unsure and point emergencies to 108.
4. **Error handling.** A refused or cut-short answer and every OpenAI error (bad key, no credit, rate limit, unknown
   model, timeout) becomes a clear message for the user instead of a crash. Translations use temperature 0.2 so
   they stay faithful and repeatable.
5. **Limits and audit.** Each user gets 100 AI requests per 24 hours (`AI_DAILY_LIMIT_PER_USER`). Every AI call is
   written to the audit log as `AI_*` with identifiers only, never medical text.

## Setup

1. Create an API key at https://platform.openai.com/api-keys (the project needs billing credit) and add it to
   `backend/.env` without quotes:
   ```
   OPENAI_API_KEY=sk-proj-...
   ```
2. Restart the backend. Without a key, the app works as before and AI pages show "AI features are not switched on yet".
3. Seed the knowledge base (already done on the development database):
   ```powershell
   .\venv\Scripts\python -m scripts.seed_knowledge_base --publish
   .\venv\Scripts\python -m scripts.seed_knowledge_base --publish --translate te hi ta kn ml   # needs the API key
   ```

Optional settings: `AI_MODEL` (default `gpt-4o-mini`), `AI_VISION_MODEL` (default `gpt-4o`), `AI_MAX_OUTPUT_TOKENS` (default 16000), `AI_TIMEOUT_SECONDS`,
`AI_DAILY_LIMIT_PER_USER`.

## New database objects (migration 0004)

- `document_analyses`: document_id (CASCADE), language_code, status (PENDING/PROCESSING/COMPLETED/FAILED),
  result_json, error, model, requested_by, timestamps. Unique on (document_id, language_code).
- `healthcare_content.content_type` (ARTICLE / FAQ / DISEASE_INFO) and `translation_group_id`, which links an
  item to its translations.

## Screens

- **Documents → Explain & translate**: simple summary, danger signs, conditions, a medicine table, what to do,
  the full translation, a glossary, and the original text.
- **AI Assistant** (patients and workers): Translate · Explain simply · Find medicines & diseases · Symptom helper.
- **Health Info**: FAQ / Diseases / Articles tabs, full-text search, and a language switcher on each item.
- **Admin → Content**: content type field, and **Translate with AI**, which creates draft copies to review and publish.

## Privacy note

Document images and medical text are sent to OpenAI's API to be processed. Before real patient use, tell users
about this, get their consent, and check your data-processing agreement and retention settings.

## Tests

`backend/tests/test_ai.py` has 17 tests with the AI calls faked, so no API usage is spent. They cover:
- text endpoints, validation and the daily limit
- the knowledge-base link in symptom answers
- the document analysis lifecycle, including reuse, `force` and failure recording
- access control: other patients, workers without a grant and admins are refused
- content types and AI translation
- handling of refusals, cut-short answers and a rejected API key
- the API key never appearing in logs

The full suite has 87 tests.
