import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.vacancy import Vacancy
from app.schemas.analysis import CandidateProfile, VacancyCriteria
from app.services.affinity import AffinityEngine, analysis_fingerprint

logger = logging.getLogger(__name__)


def _safe_analysis_error(exc: Exception) -> str:
    name = type(exc).__name__
    if name in {"LLMProviderError", "ValidationError"}:
        return "El proveedor LLM devolvió una respuesta inválida o no disponible."
    if name == "LLMConfigurationError":
        return "El proveedor LLM no está configurado."
    return "Ocurrió un error interno durante el análisis."


def stored_criteria(vacancy: Vacancy) -> VacancyCriteria | None:
    if not vacancy.ai_criteria:
        return None
    return VacancyCriteria.model_validate({"criteria": vacancy.ai_criteria["criteria"]})


def store_criteria(vacancy: Vacancy, criteria: VacancyCriteria, source: str) -> datetime:
    updated_at = datetime.now(timezone.utc)
    vacancy.ai_criteria = {"criteria": criteria.model_dump(mode="json")["criteria"], "source": source}
    vacancy.criteria_updated_at = updated_at
    return updated_at


def invalidate_analyses(db: Session, vacancy_id) -> None:
    applications = db.query(Application).filter(Application.vacancy_id == vacancy_id).all()
    for application in applications:
        application.ai_score = None
        application.ai_evidence = None
        application.analysis_status = "PENDING"
        application.analysis_error = None
        application.analyzed_at = None
        application.analyzer_version = None


def analyze_application(db: Session, application: Application, criteria: VacancyCriteria, engine: AffinityEngine) -> None:
    try:
        resume = application.resume
        # Prefer Harvard-formatted text (clean, structured) over raw OCR text when available.
        analysis_text = resume.raw_text_harvard or resume.raw_text
        if resume.extracted_profile:
            profile = CandidateProfile.model_validate(resume.extracted_profile)
        else:
            profile = engine.extract_profile(analysis_text)
            resume.extracted_profile = profile.model_dump(mode="json")
            resume.profile_extracted_at = datetime.now(timezone.utc)

        fingerprint = analysis_fingerprint(criteria, profile, engine.provider.model)
        if (
            application.analysis_status == "COMPLETED"
            and application.ai_evidence
            and application.ai_evidence.get("input_fingerprint") == fingerprint
        ):
            db.commit()
            return

        application.analysis_status = "PROCESSING"
        application.analysis_error = None
        db.commit()
        calculated_at = datetime.now(timezone.utc)
        score, evidence = engine.analyze(criteria, profile, calculated_at=calculated_at)
        application.ai_score = score
        application.ai_evidence = evidence
        application.analysis_status = "COMPLETED"
        application.analysis_error = None
        application.analyzed_at = calculated_at
        application.analyzer_version = evidence["version"]
        db.commit()
    except Exception as exc:
        db.rollback()
        failed = db.get(Application, application.id)
        failed.analysis_status = "FAILED"
        failed.analysis_error = _safe_analysis_error(exc)
        failed.ai_score = None
        failed.ai_evidence = None
        db.commit()
        logger.exception("Falló el análisis de application_id=%s", application.id)
        raise
