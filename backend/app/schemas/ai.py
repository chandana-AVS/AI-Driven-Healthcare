"""Milestone 2 AI schemas.

The *Result / Insight models are also the structured-output formats sent to OpenAI, so every field is
required and uses plain types (an empty string or list means "not present"), which keeps the JSON schema simple.
"""
import json
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TextType
from app.utils.validators import validate_language


# ----------------------------------------------------------------------------- AI output formats
class Condition(BaseModel):
    name: str = Field(description="Disease or diagnosis exactly as written in the source")
    simple_explanation: str = Field(description="What it means, in plain words, in the target language")


class Medication(BaseModel):
    name: str = Field(description="Medicine name exactly as written, in English letters")
    name_local: str = Field(description="How to say the medicine name in the target-language script; empty for English")
    dosage: str = Field(description="Strength / amount per dose exactly as written, e.g. '500 mg', '1 tablet'")
    frequency: str = Field(description="How often, in plain target-language words, e.g. 'twice a day'")
    timing: str = Field(description="When to take it (before/after food, morning/night) in the target language")
    duration: str = Field(description="For how long, in the target language; empty if not stated")
    purpose: str = Field(description="What the medicine is for, in plain target-language words; empty if not stated or not clear")
    confidence: Literal["high", "medium", "low"] = Field(
        default="high", description="How sure you are of the medicine name and dose reading (handwriting)")


class LabTest(BaseModel):
    name: str
    result: str = Field(description="Value and unit exactly as written; empty if none")
    simple_explanation: str = Field(description="What the test checks and what the result means, in plain target-language words")


class Instruction(BaseModel):
    original: str = Field(description="The instruction as written in the source")
    simple: str = Field(description="The same instruction rewritten in simple target-language words")


class Term(BaseModel):
    term: str = Field(description="Medical word or abbreviation from the source, e.g. 'BD', 'hypertension'")
    meaning: str = Field(description="Plain meaning in the target language")


class MedicalEntities(BaseModel):
    conditions: list[Condition]
    medications: list[Medication]
    tests: list[LabTest]
    instructions: list[Instruction] = Field(description="Treatment, diet, rest and care instructions")
    symptoms: list[str] = Field(description="Symptoms mentioned, in the target language")
    follow_up: str = Field(description="Next visit or review advice in the target language; empty if none")


class DocumentInsight(BaseModel):
    is_medical_document: bool
    document_kind: str = Field(description="e.g. prescription, discharge summary, lab report")
    source_language: str = Field(description="Language(s) the document is written in")
    readability: Literal["clear", "partly_unclear", "unreadable"]
    extracted_text: str = Field(description="Faithful transcription of the document text in its original language")
    summary: str = Field(description="3-6 short sentences in the target language a patient can understand")
    translation: str = Field(description="Complete translation of the document into the target language, in simple words")
    entities: MedicalEntities
    glossary: list[Term]
    warning_signs: list[str] = Field(description="Danger signs that need urgent care, in the target language")
    unclear_parts: list[str] = Field(description="Words or sections that could not be read with confidence")


class TranslationResult(BaseModel):
    detected_language: str
    translation: str = Field(description="Faithful translation into the target language")
    simplified: str = Field(description="The same content rewritten in very simple target-language words")
    key_points: list[str] = Field(description="3-6 most important points, in the target language")
    glossary: list[Term]


class SimplificationResult(BaseModel):
    simple_explanation: str
    key_points: list[str]
    guidance: list[str] = Field(description="Practical, context-based things the patient should do, in the target language")
    questions_for_doctor: list[str] = Field(description="Helpful questions the patient could ask their doctor")
    glossary: list[Term]


class ExtractionResult(BaseModel):
    summary: str = Field(description="One or two sentences in the target language")
    entities: MedicalEntities


class PossibleCause(BaseModel):
    name: str
    explanation: str = Field(description="Plain-language description in the target language")


class SymptomGuidance(BaseModel):
    urgency: Literal["EMERGENCY", "SEE_DOCTOR_TODAY", "SEE_DOCTOR_SOON", "SELF_CARE"]
    urgency_reason: str
    summary: str
    possible_causes: list[PossibleCause] = Field(description="Common causes to be aware of; never a diagnosis")
    self_care: list[str]
    see_doctor_if: list[str]
    emergency_signs: list[str]
    prevention: list[str]


class ContentTranslation(BaseModel):
    title: str
    body: str


# ----------------------------------------------------------------------------- API requests
class _LangMixin(BaseModel):
    @field_validator("target_language", "language", check_fields=False)
    @classmethod
    def _lang(cls, v):
        return validate_language(v)


class TranslateRequest(_LangMixin):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=2, max_length=20000)
    target_language: str
    text_type: TextType = TextType.GENERAL


class SimplifyRequest(_LangMixin):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=2, max_length=20000)
    language: str = "en"


class ExtractRequest(_LangMixin):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=2, max_length=20000)
    language: str = "en"


class SymptomRequest(_LangMixin):
    model_config = ConfigDict(extra="forbid")
    symptoms: str = Field(min_length=3, max_length=2000)
    language: str = "en"
    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[str] = Field(default=None, max_length=20)
    duration: Optional[str] = Field(default=None, max_length=100)


class AnalysisRequest(_LangMixin):
    model_config = ConfigDict(extra="forbid")
    language: str
    force: bool = False  # re-run even if a completed analysis exists


class ContentTranslateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    languages: list[str] = Field(min_length=1, max_length=6)

    @field_validator("languages")
    @classmethod
    def _langs(cls, v):
        return sorted({validate_language(x) for x in v})


# ----------------------------------------------------------------------------- API responses
class RelatedContent(BaseModel):
    id: uuid.UUID
    title: str
    content_type: str
    language_code: str


class SymptomResponse(SymptomGuidance):
    related_content: list[RelatedContent]
    disclaimer: str


class AIStatus(BaseModel):
    enabled: bool
    model: str
    daily_limit: int


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language_code: str
    status: str
    updated_at: datetime
    completed_at: Optional[datetime] = None


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    language_code: str
    status: str
    error: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[DocumentInsight] = None

    @classmethod
    def from_row(cls, row) -> "AnalysisOut":
        out = cls.model_validate(row)
        if row.result_json:
            out.result = DocumentInsight.model_validate(json.loads(row.result_json))
        return out
