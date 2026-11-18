"""OpenAI-powered medical language engine (Milestone 2).

All model calls go through `run_structured`, which asks the OpenAI Responses API for JSON matching a Pydantic model
(structured outputs) and turns API problems into clear HTTP errors. Tests replace `_client` / the task functions with
fakes, so they never call the API.
"""
import base64
import logging
from datetime import timedelta
from functools import lru_cache
from typing import TypeVar

import openai
from fastapi import HTTPException, status
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuditLog, User
from app.models.enums import LANGUAGE_NAMES, TextType
from app.models.mixins import utcnow
from app.utils.image_prep import prepare_image
from app.schemas.ai import (
    ContentTranslation,
    DocumentInsight,
    ExtractionResult,
    SimplificationResult,
    SymptomGuidance,
    TranslationResult,
)

logger = logging.getLogger("ai")
T = TypeVar("T", bound=BaseModel)

NOT_CONFIGURED = "AI features are not configured. Set OPENAI_API_KEY in backend/.env and restart the backend."


class AIError(HTTPException):
    pass


def ai_enabled() -> bool:
    return bool(settings.ai_api_key)


@lru_cache
def _client() -> OpenAI:
    return OpenAI(api_key=settings.ai_api_key, timeout=settings.AI_TIMEOUT_SECONDS, max_retries=2)


def language_name(code: str) -> str:
    info = LANGUAGE_NAMES.get(code, {"name": code, "native": code})
    return f"{info['name']} ({info['native']})"


def _to_openai_content(content: list[dict]) -> list[dict]:
    """Convert the internal content blocks (text / image / document) into Responses API input parts."""
    parts = []
    for block in content:
        if block["type"] == "text":
            parts.append({"type": "input_text", "text": block["text"]})
        elif block["type"] == "image":
            src = block["source"]
            parts.append({"type": "input_image", "detail": "high",
                          "image_url": f"data:{src['media_type']};base64,{src['data']}"})
        elif block["type"] == "document":
            src = block["source"]
            parts.append({"type": "input_file", "filename": "medical_document.pdf",
                          "file_data": f"data:{src['media_type']};base64,{src['data']}"})
    return parts


def run_structured(system: str, content: list[dict], output: type[T], *, max_tokens: int | None = None,
                   model: str | None = None, temperature: float = 0.2) -> T:
    """Call OpenAI and return a validated instance of `output`."""
    if not ai_enabled():
        raise AIError(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=NOT_CONFIGURED)

    model = model or settings.AI_MODEL
    params = dict(
        model=model,
        instructions=system,
        input=[{"role": "user", "content": _to_openai_content(content)}],
        text_format=output,
        max_output_tokens=min(max_tokens or settings.AI_MAX_OUTPUT_TOKENS, settings.AI_MAX_OUTPUT_TOKENS),
    )
    if model.startswith(("gpt-4", "gpt-3.5")):
        params["temperature"] = temperature  # low = faithful, repeatable output; reasoning models do not accept it

    try:
        response = _client().responses.parse(**params)
    except openai.AuthenticationError:
        logger.error("OpenAI rejected the API key (401)")
        raise AIError(status_code=503, detail="OpenAI rejected the API key. Create a new key at "
                                              "https://platform.openai.com/api-keys, put it in OPENAI_API_KEY and restart.")
    except openai.PermissionDeniedError:
        logger.error("OpenAI permission denied for model %s (403)", model)
        raise AIError(status_code=503, detail=f"This OpenAI key cannot use the model '{model}'. "
                                              "Check the key's project permissions or change AI_MODEL / AI_VISION_MODEL.")
    except openai.RateLimitError as exc:
        quota = "insufficient_quota" in str(exc)
        logger.error("OpenAI rate limit / quota: %s", exc)
        raise AIError(status_code=503, detail="The OpenAI account has no credit left. Add billing at "
                                              "https://platform.openai.com/settings/organization/billing."
                      if quota else "OpenAI rate limit reached. Please try again in a minute.")
    except openai.NotFoundError:
        logger.error("OpenAI model not found: %s", model)
        raise AIError(status_code=503, detail=f"OpenAI model '{model}' was not found. Check AI_MODEL / AI_VISION_MODEL.")
    except openai.BadRequestError as exc:
        logger.error("OpenAI bad request: %s", exc)
        raise AIError(status_code=422, detail="OpenAI could not process this input. Try a smaller or clearer file.")
    except (openai.APITimeoutError, openai.APIConnectionError):
        logger.exception("Could not reach OpenAI")
        raise AIError(status_code=504, detail="Could not reach the AI service. Check the internet connection and try again.")
    except openai.APIError:
        logger.exception("OpenAI request failed")
        raise AIError(status_code=502, detail="The AI service returned an error. Please try again.")

    if response.status == "incomplete":
        reason = getattr(response.incomplete_details, "reason", None)
        if reason == "content_filter":
            raise AIError(status_code=422, detail="The AI declined to process this content.")
        raise AIError(status_code=502, detail="The AI response was cut short. Try a shorter text or document.")

    parsed = response.output_parsed
    if parsed is None:  # model refused or returned no structured output
        raise AIError(status_code=422, detail="The AI could not produce a structured answer for this input.")

    if response.usage:
        logger.info("OpenAI %s %s: input=%s output=%s tokens", model, output.__name__,
                    response.usage.input_tokens, response.usage.output_tokens)
    return parsed


# ----------------------------------------------------------------------------- usage limit
def enforce_daily_limit(db: Session, user: User) -> None:
    since = utcnow() - timedelta(hours=24)
    used = (db.query(AuditLog)
            .filter(AuditLog.actor_id == user.id, AuditLog.action.like("AI\\_%", escape="\\"), AuditLog.created_at >= since)
            .count())
    if used >= settings.AI_DAILY_LIMIT_PER_USER:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Daily AI limit reached ({settings.AI_DAILY_LIMIT_PER_USER} requests). Try again tomorrow.")


# ----------------------------------------------------------------------------- prompts
BASE_RULES = """You are the medical language assistant of a healthcare platform for rural communities in India.
Your readers are patients and families who may have little schooling and no medical training.

Rules that always apply:
- Use only information in the provided text or document. Never add diagnoses, medicines, doses or results that are not there.
- Copy medicine names, strengths, doses, numbers, units and dates exactly. Never change, round or "correct" a dose.
- If something is hard to read or ambiguous, say so (list it as unclear) instead of guessing.
- Write explanations in short, everyday sentences, the way a kind community health worker would speak. Explain any medical word you must use.
- Write in the requested language using its own script. Keep medicine names in English letters; numbers as digits.
- Do not tell the patient to stop, start or change any medicine; tell them to ask their doctor.
- Use an empty string or empty list for anything that is not present."""

TEXT_TYPE_HINTS = {
    TextType.PRESCRIPTION: "The text is a prescription. Keep every medicine with its dose, frequency, timing and duration.",
    TextType.DISCHARGE_SUMMARY: "The text is a hospital discharge summary. Keep diagnoses, treatment given, medicines at discharge, follow-up and warning signs.",
    TextType.INSTRUCTIONS: "The text is a set of healthcare instructions. Keep every step and its order.",
    TextType.GENERAL: "The text is general health information.",
}


def _text_block(label: str, text: str) -> dict:
    return {"type": "text", "text": f"<{label}>\n{text}\n</{label}>"}


HANDWRITING_GUIDE = """How to read Indian handwritten prescriptions:
- Abbreviations: Rx = prescription; T. / Tab = tablet; Cap = capsule; Syp / Syr = syrup; Inj = injection; Oint = ointment;
  c/o = complaints of; O/E = on examination; H/o = history of; Adv = advice; Dx = diagnosis; Ix = investigations;
  OD = once a day; BD = twice a day; TDS = three times a day; QID = four times a day; HS = at bedtime; SOS = only when needed;
  AC = before food; PC = after food; stat = immediately; x 5 days / x 1 week / x 3 month = duration.
- Dose patterns like 1-0-1 mean morning-afternoon-night (1-0-1 = morning and night; 1-0-0 = morning only; 0-0-1 = night only;
  1-1-1 = three times a day). A circled number or 'i', 'ii' before a medicine is just its list number.
- Words written beside a bracket (e.g. "after meals" next to a bracket spanning two medicines) apply to every medicine in that bracket.
- Medicine names are usually Indian brand names (e.g. Augmentin, Pan-D, Dolo, Ferium XT, Becosules, Limcee, Shelcal, Enzoflam,
  Hexigel, Zerodol, Rantac, Livogen, Bevon). Use the letter shapes to find the most likely real brand name. If you are not sure,
  write your best reading, set confidence to "low" or "medium", and add the raw reading to unclear_parts
  (e.g. "T. Fern...i - maybe Ferium XT").
- Printed letterhead text (doctor, clinic, phone, address) is not part of the prescription; mention it only in extracted_text.
- Durations are often written to the right of, or on the line below, a medicine or its dose pattern (e.g. 'x 5 days', '3 month', '1 week'); look there for every medicine and fill in duration when you find it.
- Confidence: use "high" only when every letter of the name and the dose is clearly legible. A guessed brand name is "medium" at most, and "low" when several brands would fit the letter shapes.
- Never invent a dose, frequency or duration that is not written. If a number is unreadable, leave that field empty and list it as unclear."""


def analyze_document_file(content: bytes, mime_type: str, document_type: str, language: str) -> DocumentInsight:
    if mime_type == "application/pdf":
        data = base64.standard_b64encode(content).decode("ascii")
        file_blocks = [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}}]
        view_note = ""
    else:
        images, prepared_type = prepare_image(content)
        media_type = prepared_type or mime_type
        file_blocks = [{"type": "image", "source": {"type": "base64", "media_type": media_type,
                                                    "data": base64.standard_b64encode(img).decode("ascii")}}
                       for img in images]
        view_note = ("The first image is the whole page. The following images are zoomed-in, overlapping strips of the same page, "
                     "from top to bottom, so you can read small handwriting. Use them all, and do not list a line twice "
                     "because it appears in two strips.\n" if len(images) > 1 else "")
    task = (
        f"{view_note}Read this medical document (uploaded as: {document_type.replace('_', ' ').lower()}). "
        f"The target language is {language_name(language)}.\n"
        "1. Transcribe all readable text faithfully in its original language (extracted_text), line by line, keeping the "
        "layout. Handwriting may be messy: study each word carefully, and list anything you are unsure of under unclear_parts.\n"
        "2. Extract the medical entities: conditions/complaints, medicines (with dose, frequency, timing, duration), tests and "
        "results, instructions, symptoms and follow-up. Expand dose patterns like 1-0-1 into plain words.\n"
        "3. Write a short summary and a complete translation in the target language using simple words.\n"
        "4. Add a glossary for medical words and abbreviations used in the document.\n"
        "5. List danger signs that need urgent care only if the document mentions them or they clearly apply to its diagnoses.\n"
        "If the file is not a medical document, set is_medical_document to false and leave the medical fields empty."
    )
    return run_structured(BASE_RULES + "\n\n" + HANDWRITING_GUIDE, [*file_blocks, {"type": "text", "text": task}],
                          DocumentInsight, model=settings.AI_VISION_MODEL, temperature=0)


def translate_text(text: str, target_language: str, text_type: TextType) -> TranslationResult:
    task = (f"Translate the medical text below into {language_name(target_language)}. {TEXT_TYPE_HINTS[text_type]}\n"
            "Give a faithful translation, then a simplified version a patient can follow, the key points, and a glossary.\n"
            "In the translation and simplified version:\n"
            "- Write each medicine name in English letters exactly as in the source (e.g. 'Amlodipine'), never transliterated "
            "and never mixing two scripts in one word.\n"
            "- Replace dosing abbreviations (OD, BD, TDS, QID, SOS, HS, AC, PC, Tab, Cap, Inj) with their meaning in the target "
            "language, e.g. 'BD' -> 'twice a day' in the target language.\n"
            "- Keep doses, units and numbers exactly as written (e.g. '500mg', '30 days').")
    return run_structured(BASE_RULES, [{"type": "text", "text": task}, _text_block("medical_text", text)], TranslationResult)


def simplify_text(text: str, language: str) -> SimplificationResult:
    task = (f"Explain the medical text below in very simple {language_name(language)}. Replace medical terms with everyday words, "
            "give practical guidance on what the patient should do based on this text, suggest questions to ask the doctor, "
            "and add a glossary of the medical terms.")
    return run_structured(BASE_RULES, [{"type": "text", "text": task}, _text_block("medical_text", text)], SimplificationResult)


def extract_entities(text: str, language: str) -> ExtractionResult:
    task = (f"Identify the diseases, medicines, tests, treatment instructions, symptoms and follow-up in the medical text below. "
            f"Write explanations in {language_name(language)}.")
    return run_structured(BASE_RULES, [{"type": "text", "text": task}, _text_block("medical_text", text)], ExtractionResult)


SYMPTOM_RULES = BASE_RULES + """

You are now giving health awareness information about symptoms. This is not a diagnosis.
- Choose urgency carefully. Use EMERGENCY for danger signs such as chest pain, difficulty breathing, fainting,
  seizures, confusion, severe bleeding, signs of stroke, very high fever in an infant, severe dehydration,
  or pregnancy with bleeding, severe pain or reduced baby movement. When unsure between two levels, choose the more urgent one.
- For EMERGENCY, the summary must first tell the person to go to the nearest hospital or call 108 now.
- List common, relevant causes only, described as possibilities to discuss with a doctor.
- Self-care advice must be safe for anyone (rest, fluids, ORS, hygiene). Never name prescription medicines or doses.
- Prefer facts from the knowledge base articles provided, when they are relevant."""


def symptom_guidance(symptoms: str, language: str, age: int | None, gender: str | None, duration: str | None,
                     knowledge: list[tuple[str, str]]) -> SymptomGuidance:
    profile = ", ".join(x for x in [f"age {age}" if age is not None else "", gender or "",
                                    f"for {duration}" if duration else ""] if x) or "not given"
    kb = "\n\n".join(f"### {title}\n{body[:2500]}" for title, body in knowledge) or "(no matching articles)"
    task = (f"Write the answer in {language_name(language)}. Person: {profile}.\n"
            "Give awareness information about these symptoms: urgency level and reason, a short summary, possible causes, "
            "safe self-care, when to see a doctor, emergency signs and prevention.")
    content = [_text_block("knowledge_base", kb), {"type": "text", "text": task}, _text_block("symptoms", symptoms)]
    return run_structured(SYMPTOM_RULES, content, SymptomGuidance)


def translate_content(title: str, body: str, target_language: str) -> ContentTranslation:
    task = (f"Translate this health education article into {language_name(target_language)} for rural readers. "
            "Keep the meaning and structure (paragraphs, lists) and use simple everyday words. Translate the title too.")
    return run_structured(BASE_RULES, [{"type": "text", "text": task},
                                       _text_block("title", title), _text_block("body", body)], ContentTranslation)
