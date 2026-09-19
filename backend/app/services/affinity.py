import re
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Protocol

from app.schemas.analysis import CandidateProfile, SemanticAssessment, VacancyCriteria, VacancyCriteriaDraft, VacancyCriterion
from app.services.llm_client import LLMProviderError

ENGINE_VERSION = "skills-activities-v1"


class AnalysisProvider(Protocol):
    model: str

    def extract_vacancy_criteria(self, title: str, description: str, requirements: str) -> VacancyCriteriaDraft: ...
    def extract_candidate_profile(self, raw_text: str) -> CandidateProfile: ...
    def match(self, criteria: VacancyCriteria, profile: CandidateProfile) -> SemanticAssessment: ...


def normalize_weights(criteria: VacancyCriteria | VacancyCriteriaDraft) -> VacancyCriteria:
    raw_weights = [float(getattr(item, "weight", getattr(item, "importance", 1))) for item in criteria.criteria]
    total = sum(raw_weights)
    if total <= 0:
        raise ValueError("La suma de pesos debe ser mayor que cero.")
    normalized = [round(value * 100 / total, 4) for value in raw_weights]
    normalized[-1] = round(normalized[-1] + (100 - sum(normalized)), 4)
    return VacancyCriteria(criteria=[
        VacancyCriterion(name=item.name, kind=item.kind, description=item.description, weight=normalized[index])
        for index, item in enumerate(criteria.criteria)
    ])


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def sanitize_profile(profile: CandidateProfile, raw_text: str) -> CandidateProfile:
    """Discard claims whose quote cannot be traced to the extracted CV text."""
    searchable = _collapse_whitespace(raw_text)
    return CandidateProfile(claims=[
        claim for claim in profile.claims if _collapse_whitespace(claim.evidence_quote) in searchable
    ])


def analysis_fingerprint(criteria: VacancyCriteria, profile: CandidateProfile, model: str) -> str:
    canonical = json.dumps(
        {
            "engine": ENGINE_VERSION,
            "model": model,
            "criteria": normalize_weights(criteria).model_dump(mode="json"),
            "profile": profile.model_dump(mode="json"),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def calculate_affinity(
    criteria: VacancyCriteria,
    profile: CandidateProfile,
    assessment: SemanticAssessment,
    *,
    model: str,
    calculated_at: datetime | None = None,
) -> tuple[int, dict[str, Any]]:
    criteria = normalize_weights(criteria)
    matches_by_criterion = {}
    for match in assessment.matches:
        if match.criterion_index >= len(criteria.criteria):
            raise LLMProviderError("El LLM devolvió un criterion_index inválido.")
        if match.criterion_index in matches_by_criterion:
            raise LLMProviderError("El LLM duplicó un criterio en la evaluación.")
        if match.claim_index is not None and match.claim_index >= len(profile.claims):
            raise LLMProviderError("El LLM devolvió un claim_index inválido.")
        matches_by_criterion[match.criterion_index] = match
    if set(matches_by_criterion) != set(range(len(criteria.criteria))):
        raise LLMProviderError("El LLM no evaluó exactamente todos los criterios.")

    factors = []
    total = 0.0
    for index, criterion in enumerate(criteria.criteria):
        match = matches_by_criterion[index]
        contribution = round(criterion.weight * match.strength, 2)
        total += contribution
        claim = profile.claims[match.claim_index] if match.claim_index is not None else None
        factors.append({
            "criterion": criterion.name,
            "kind": criterion.kind.value,
            "weight": criterion.weight,
            "match_strength": match.strength,
            "contribution": contribution,
            "matched_claim": claim.name if claim else None,
            "evidence_quote": claim.evidence_quote if claim else None,
            "evidence_section": claim.section if claim else None,
            "rationale": match.rationale,
        })

    timestamp = calculated_at or datetime.now(timezone.utc)
    score = max(0, min(100, round(total)))
    evidence = {
        "version": ENGINE_VERSION,
        "calculated_at": timestamp.isoformat(),
        "model": model,
        "input_fingerprint": analysis_fingerprint(criteria, profile, model),
        "methodology": "Suma ponderada de habilidades y actividades; excluye educación y duración de experiencia.",
        "factors": factors,
        "covered": [factor["criterion"] for factor in factors if factor["match_strength"] > 0],
        "uncovered": [factor["criterion"] for factor in factors if factor["match_strength"] == 0],
    }
    return score, evidence


class AffinityEngine:
    def __init__(self, provider: AnalysisProvider):
        self.provider = provider

    def extract_criteria(self, title: str, description: str, requirements: str) -> VacancyCriteria:
        return normalize_weights(self.provider.extract_vacancy_criteria(title, description, requirements))

    def extract_profile(self, raw_text: str) -> CandidateProfile:
        return sanitize_profile(self.provider.extract_candidate_profile(raw_text), raw_text)

    def analyze(self, criteria: VacancyCriteria, profile: CandidateProfile, *, calculated_at: datetime | None = None):
        if profile.claims:
            assessment = self.provider.match(criteria, profile)
        else:
            assessment = SemanticAssessment(matches=[{
                "criterion_index": index,
                "claim_index": None,
                "strength": 0.0,
                "rationale": "El CV no contiene evidencia verificable para este criterio.",
            } for index in range(len(criteria.criteria))])
        return calculate_affinity(criteria, profile, assessment, model=self.provider.model, calculated_at=calculated_at)
