from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CriterionKind(str, Enum):
    SKILL = "SKILL"
    ACTIVITY = "ACTIVITY"


class VacancyCriterion(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    kind: CriterionKind
    description: str = Field(max_length=500)
    weight: float = Field(gt=0, le=100)

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class VacancyCriteria(StrictModel):
    criteria: list[VacancyCriterion] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_names(self):
        names = [criterion.name.casefold() for criterion in self.criteria]
        if len(names) != len(set(names)):
            raise ValueError("Los criterios no pueden repetirse.")
        return self


class VacancyCriterionDraft(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    kind: CriterionKind
    description: str = Field(max_length=500)
    importance: int = Field(ge=1, le=5)


class VacancyCriteriaDraft(StrictModel):
    criteria: list[VacancyCriterionDraft] = Field(min_length=1, max_length=30)


class CandidateClaim(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    kind: CriterionKind
    evidence_quote: str = Field(min_length=1, max_length=700)
    section: str = Field(max_length=120)


class CandidateProfile(StrictModel):
    claims: list[CandidateClaim] = Field(max_length=100)


class SemanticMatch(StrictModel):
    criterion_index: int = Field(ge=0)
    claim_index: int | None = Field(ge=0)
    strength: Literal[0.0, 0.5, 1.0]
    rationale: str = Field(min_length=1, max_length=400)

    @model_validator(mode="after")
    def validate_claim_reference(self):
        if self.strength == 0 and self.claim_index is not None:
            raise ValueError("Una no coincidencia no debe referenciar evidencia.")
        if self.strength > 0 and self.claim_index is None:
            raise ValueError("Una coincidencia debe referenciar evidencia.")
        return self


class SemanticAssessment(StrictModel):
    matches: list[SemanticMatch]


class AnalysisResultOut(BaseModel):
    application_id: UUID
    score: int | None
    analysis_status: str
    analyzed_at: datetime | None = None
    error: str | None = None


class AnalysisRunOut(BaseModel):
    vacancy_id: UUID
    analyzed: int
    failed: int
    results: list[AnalysisResultOut]


class CriteriaOut(VacancyCriteria):
    updated_at: datetime
    source: Literal["LLM", "HUMAN"]
