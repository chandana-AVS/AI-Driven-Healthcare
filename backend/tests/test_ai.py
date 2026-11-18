"""Milestone 2 AI engine tests. OpenAI is never called: the ai_service functions are replaced with fakes."""
from types import SimpleNamespace

import pytest

from app.config import settings
from app.schemas import ai as s
from app.services import ai_service
from tests.conftest import API, upload

ENTITIES = s.MedicalEntities(
    conditions=[s.Condition(name="Hypertension", simple_explanation="High blood pressure")],
    medications=[s.Medication(name="Amlodipine", name_local="", dosage="5 mg", frequency="once a day",
                              timing="morning", duration="30 days", purpose="lowers blood pressure")],
    tests=[], instructions=[s.Instruction(original="Low salt diet", simple="Eat less salt")],
    symptoms=["headache"], follow_up="Review after 1 month",
)
INSIGHT = s.DocumentInsight(
    is_medical_document=True, document_kind="prescription", source_language="English", readability="clear",
    extracted_text="Tab Amlodipine 5mg OD x 30 days", summary="Take one tablet every morning for blood pressure.",
    translation="ప్రతి ఉదయం ఒక మాత్ర", entities=ENTITIES, glossary=[s.Term(term="OD", meaning="once a day")],
    warning_signs=["Severe headache"], unclear_parts=[],
)


@pytest.fixture
def ai_on(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    calls = []

    def record(name, value):
        def fake(*args, **kwargs):
            calls.append((name, args))
            return value
        return fake

    monkeypatch.setattr(ai_service, "translate_text", record("translate", s.TranslationResult(
        detected_language="English", translation="అనువాదం", simplified="సులభంగా", key_points=["one"], glossary=[])))
    monkeypatch.setattr(ai_service, "simplify_text", record("simplify", s.SimplificationResult(
        simple_explanation="simple", key_points=[], guidance=["rest"], questions_for_doctor=[], glossary=[])))
    monkeypatch.setattr(ai_service, "extract_entities", record("extract", s.ExtractionResult(summary="bp", entities=ENTITIES)))
    monkeypatch.setattr(ai_service, "symptom_guidance", record("symptoms", s.SymptomGuidance(
        urgency="SEE_DOCTOR_SOON", urgency_reason="fever for 3 days", summary="Possible infection",
        possible_causes=[s.PossibleCause(name="Viral fever", explanation="common")], self_care=["Drink fluids"],
        see_doctor_if=["Fever above 3 days"], emergency_signs=["Confusion"], prevention=["Use mosquito nets"])))
    monkeypatch.setattr(ai_service, "analyze_document_file", record("analyze", INSIGHT))
    monkeypatch.setattr(ai_service, "translate_content", lambda title, body, lang: s.ContentTranslation(
        title=f"[{lang}] {title}", body=f"[{lang}] {body}"))
    return calls


# ----------------------------------------------------------------------------- text endpoints
def test_ai_requires_login(client):
    assert client.post(f"{API}/ai/translate", json={"text": "x y", "target_language": "te"}).status_code == 401


def test_ai_not_configured_returns_503(client, patient, monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    status = client.get(f"{API}/ai/status", headers=patient["headers"]).json()
    assert status["enabled"] is False
    res = client.post(f"{API}/ai/simplify", headers=patient["headers"], json={"text": "Take BD after food", "language": "hi"})
    assert res.status_code == 503 and "OPENAI_API_KEY" in res.json()["detail"]


def test_translate_simplify_extract(client, patient, ai_on):
    h = patient["headers"]
    res = client.post(f"{API}/ai/translate", headers=h,
                      json={"text": "Tab Amlodipine 5mg OD", "target_language": "te", "text_type": "PRESCRIPTION"})
    assert res.status_code == 200, res.text
    assert res.json()["translation"] == "అనువాదం"
    assert client.post(f"{API}/ai/simplify", headers=h, json={"text": "HTN on CCB", "language": "hi"}).status_code == 200
    ext = client.post(f"{API}/ai/extract", headers=h, json={"text": "HTN, Amlodipine 5mg"})
    assert ext.json()["entities"]["medications"][0]["dosage"] == "5 mg"
    assert [c[0] for c in ai_on] == ["translate", "simplify", "extract"]


def test_translate_validation(client, patient, ai_on):
    h = patient["headers"]
    assert client.post(f"{API}/ai/translate", headers=h, json={"text": "hello", "target_language": "fr"}).status_code == 422
    assert client.post(f"{API}/ai/translate", headers=h, json={"text": "", "target_language": "te"}).status_code == 422
    assert client.post(f"{API}/ai/translate", headers=h,
                       json={"text": "hello", "target_language": "te", "text_type": "POEM"}).status_code == 422


def test_daily_limit(client, patient, ai_on, monkeypatch):
    monkeypatch.setattr(settings, "AI_DAILY_LIMIT_PER_USER", 1)
    body = {"text": "Take rest", "language": "en"}
    assert client.post(f"{API}/ai/simplify", headers=patient["headers"], json=body).status_code == 200
    assert client.post(f"{API}/ai/simplify", headers=patient["headers"], json=body).status_code == 429


def test_symptoms_uses_knowledge_base(client, patient, admin, ai_on):
    item = client.post(f"{API}/admin/content", headers=admin["headers"], json={
        "title": "Dengue fever", "body": "Dengue causes high fever and body pain. Drink fluids.",
        "category": "COMMON_DISEASES", "content_type": "DISEASE_INFO", "status": "PUBLISHED"}).json()
    res = client.post(f"{API}/ai/symptoms", headers=patient["headers"],
                      json={"symptoms": "high fever and body pain", "language": "en", "age": 30, "duration": "3 days"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["urgency"] == "SEE_DOCTOR_SOON"
    assert body["related_content"][0]["id"] == item["id"]
    assert "108" in body["disclaimer"]


# ----------------------------------------------------------------------------- document analysis
def _upload(client, patient):
    res = upload(client, patient["headers"])
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_document_analysis_flow(client, patient, ai_on):
    doc_id = _upload(client, patient)
    h = patient["headers"]
    assert client.get(f"{API}/documents/{doc_id}/analysis?language=te", headers=h).status_code == 404
    res = client.post(f"{API}/documents/{doc_id}/analysis", headers=h, json={"language": "te"})
    assert res.status_code == 202, res.text
    got = client.get(f"{API}/documents/{doc_id}/analysis?language=te", headers=h).json()
    assert got["status"] == "COMPLETED"
    assert got["result"]["entities"]["medications"][0]["name"] == "Amlodipine"
    assert client.get(f"{API}/documents/{doc_id}", headers=h).json()["processing_status"] == "PROCESSED"

    # A completed analysis is reused unless force=true.
    client.post(f"{API}/documents/{doc_id}/analysis", headers=h, json={"language": "te"})
    assert sum(1 for c in ai_on if c[0] == "analyze") == 1
    client.post(f"{API}/documents/{doc_id}/analysis", headers=h, json={"language": "te", "force": True})
    assert sum(1 for c in ai_on if c[0] == "analyze") == 2


def test_document_analysis_access_control(client, patient, other_patient, worker, admin, ai_on):
    doc_id = _upload(client, patient)
    for who in (other_patient, worker):  # worker has no grant
        assert client.post(f"{API}/documents/{doc_id}/analysis", headers=who["headers"],
                           json={"language": "en"}).status_code == 404
    assert client.post(f"{API}/documents/{doc_id}/analysis", headers=admin["headers"],
                       json={"language": "en"}).status_code in (403, 404)
    assert not any(c[0] == "analyze" for c in ai_on)


def test_document_analysis_failure_is_recorded(client, patient, ai_on, monkeypatch):
    def boom(*a, **k):
        raise ai_service.AIError(status_code=422, detail="The AI declined to process this content.")
    monkeypatch.setattr(ai_service, "analyze_document_file", boom)
    doc_id = _upload(client, patient)
    client.post(f"{API}/documents/{doc_id}/analysis", headers=patient["headers"], json={"language": "hi"})
    got = client.get(f"{API}/documents/{doc_id}/analysis?language=hi", headers=patient["headers"]).json()
    assert got["status"] == "FAILED" and "declined" in got["error"]


# ----------------------------------------------------------------------------- knowledge base
def test_knowledge_base_types_and_auto_translation(client, admin, ai_on):
    h = admin["headers"]
    faq = client.post(f"{API}/admin/content", headers=h, json={
        "title": "How do I make ORS at home?", "body": "Mix 6 level teaspoons of sugar and half a teaspoon of salt in 1 litre of clean water.",
        "category": "GENERAL_HEALTH", "content_type": "FAQ", "status": "PUBLISHED"}).json()
    assert faq["content_type"] == "FAQ"
    listed = client.get(f"{API}/content?content_type=FAQ").json()
    assert [c["id"] for c in listed] == [faq["id"]]
    assert client.get(f"{API}/content?content_type=DISEASE_INFO").json() == []

    res = client.post(f"{API}/admin/content/{faq['id']}/translate", headers=h, json={"languages": ["te", "hi", "en"]})
    assert res.status_code == 201, res.text
    copies = res.json()
    assert sorted(c["language_code"] for c in copies) == ["hi", "te"]  # source language skipped
    assert all(c["status"] == "DRAFT" and c["translation_group_id"] == faq["id"] for c in copies)
    assert client.post(f"{API}/admin/content/{faq['id']}/translate", headers=h,
                       json={"languages": ["te"]}).status_code == 409

    client.patch(f"{API}/admin/content/{copies[0]['id']}", headers=h, json={"status": "PUBLISHED"})
    versions = client.get(f"{API}/content/{faq['id']}/translations").json()
    assert len(versions) == 2  # the original + the one published copy


def test_search_matches_body(client, admin):
    client.post(f"{API}/admin/content", headers=admin["headers"], json={
        "title": "Staying healthy in monsoon", "body": "Boil drinking water to prevent typhoid.",
        "category": "PREVENTIVE_HEALTHCARE", "status": "PUBLISHED"})
    assert len(client.get(f"{API}/content?search=typhoid").json()) == 1


# ----------------------------------------------------------------------------- run_structured guards
class _FakeClient:
    def __init__(self, response=None, exc=None):
        self.response, self.exc = response, exc
        self.responses = SimpleNamespace(parse=self._parse)

    def _parse(self, **kwargs):
        self.kwargs = kwargs
        if self.exc:
            raise self.exc
        return self.response


def _resp(status, parsed, reason=None):
    return SimpleNamespace(status=status, output_parsed=parsed,
                           incomplete_details=SimpleNamespace(reason=reason) if reason else None,
                           usage=SimpleNamespace(input_tokens=1, output_tokens=1))


def test_run_structured_handles_response_states(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    ok = s.ContentTranslation(title="t", body="b")
    fake = _FakeClient(_resp("completed", ok))
    monkeypatch.setattr(ai_service, "_client", lambda: fake)
    assert ai_service.run_structured("sys", [{"type": "text", "text": "x"}], s.ContentTranslation) == ok
    assert fake.kwargs["model"] == settings.AI_MODEL and fake.kwargs["text_format"] is s.ContentTranslation
    assert fake.kwargs["instructions"] == "sys"
    assert fake.kwargs["input"][0]["content"] == [{"type": "input_text", "text": "x"}]
    assert fake.kwargs["max_output_tokens"] <= 16384

    for resp, code in ((_resp("completed", None), 422),
                       (_resp("incomplete", None, "max_output_tokens"), 502),
                       (_resp("incomplete", None, "content_filter"), 422)):
        monkeypatch.setattr(ai_service, "_client", lambda resp=resp: _FakeClient(resp))
        with pytest.raises(ai_service.AIError) as err:
            ai_service.run_structured("sys", [], s.ContentTranslation)
        assert err.value.status_code == code


def test_run_structured_maps_bad_api_key(monkeypatch):
    import httpx
    import openai
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-wrong")
    req = httpx.Request("POST", "https://api.openai.com/v1/responses")
    exc = openai.AuthenticationError("bad key", response=httpx.Response(401, request=req), body=None)
    monkeypatch.setattr(ai_service, "_client", lambda: _FakeClient(exc=exc))
    with pytest.raises(ai_service.AIError) as err:
        ai_service.run_structured("sys", [], s.ContentTranslation)
    assert err.value.status_code == 503 and "OPENAI_API_KEY" in err.value.detail


def test_api_key_hidden_from_settings_repr(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-secret-value")
    assert "sk-secret-value" not in repr(settings)


# ----------------------------------------------------------------------------- saved translations
def test_saved_translations_are_listed(client, patient, other_patient, ai_on):
    doc_id = _upload(client, patient)
    h = patient["headers"]
    assert client.get(f"{API}/documents/{doc_id}/analyses", headers=h).json() == []
    for lang in ("te", "hi"):
        client.post(f"{API}/documents/{doc_id}/analysis", headers=h, json={"language": lang})
    saved = client.get(f"{API}/documents/{doc_id}/analyses", headers=h).json()
    assert {a["language_code"] for a in saved} == {"te", "hi"} and all(a["status"] == "COMPLETED" for a in saved)
    assert set(client.get(f"{API}/documents/{doc_id}", headers=h).json()["translated_languages"]) == {"te", "hi"}
    # Another patient cannot discover which translations exist.
    assert client.get(f"{API}/documents/{doc_id}/analyses", headers=other_patient["headers"]).status_code == 404


# ----------------------------------------------------------------------------- handwriting support
def test_tall_photo_is_split_into_zoomed_strips():
    import io
    from PIL import Image
    from app.utils.image_prep import prepare_image
    buf = io.BytesIO()
    Image.new("RGB", (900, 1600), "white").save(buf, format="JPEG")
    images, mime = prepare_image(buf.getvalue())
    assert mime == "image/jpeg" and len(images) >= 3          # full page + strips
    square = io.BytesIO()
    Image.new("RGB", (1000, 1000), "white").save(square, format="PNG")
    assert len(prepare_image(square.getvalue())[0]) == 1     # nothing to zoom
    assert prepare_image(b"not an image") == ([b"not an image"], "")


def test_document_reading_uses_vision_model_and_high_detail(monkeypatch):
    import io
    from PIL import Image
    captured = {}
    monkeypatch.setattr(ai_service, "run_structured", lambda system, content, output, **kw: captured.update(
        system=system, content=content, **kw) or INSIGHT)
    buf = io.BytesIO()
    Image.new("RGB", (900, 1600), "white").save(buf, format="JPEG")
    ai_service.analyze_document_file(buf.getvalue(), "image/jpeg", "PRESCRIPTION", "te")
    assert captured["model"] == settings.AI_VISION_MODEL
    assert "1-0-1" in captured["system"]
    assert sum(1 for b in captured["content"] if b["type"] == "image") >= 3
    parts = ai_service._to_openai_content([b for b in captured["content"] if b["type"] == "image"][:1])
    assert parts[0]["detail"] == "high"
