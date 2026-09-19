from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.models.application import Application
from app.models.user import UserRole
from app.models.vacancy import Vacancy
from app.schemas.analysis import AnalysisResultOut, AnalysisRunOut, CriteriaOut, VacancyCriteria
from app.services.affinity import AffinityEngine, normalize_weights
from app.services.analyzer import analyze_application, invalidate_analyses, store_criteria, stored_criteria
from app.services.llm_client import LLMConfigurationError, LLMProviderError, OpenAIAnalysisClient

router = APIRouter()


def get_analysis_engine() -> AffinityEngine:
    try:
        return AffinityEngine(OpenAIAnalysisClient())
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _owned_vacancy(vacancy_id: str, db: SessionDep, current_user: CurrentUser) -> Vacancy:
    if current_user.role != UserRole.RECRUITER:
        raise HTTPException(status_code=403, detail="Solo los reclutadores pueden ejecutar análisis.")
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacante no encontrada.")
    if str(vacancy.recruiter_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta vacante.")
    return vacancy


def _criteria_response(vacancy: Vacancy) -> CriteriaOut:
    criteria = stored_criteria(vacancy)
    if criteria is None or vacancy.criteria_updated_at is None:
        raise HTTPException(status_code=404, detail="La vacante todavía no tiene criterios extraídos.")
    return CriteriaOut(
        criteria=criteria.criteria,
        updated_at=vacancy.criteria_updated_at,
        source=vacancy.ai_criteria.get("source", "LLM"),
    )


@router.get("/vacancies/{vacancy_id}/criteria", response_model=CriteriaOut)
def get_criteria(vacancy_id: str, db: SessionDep, current_user: CurrentUser) -> Any:
    return _criteria_response(_owned_vacancy(vacancy_id, db, current_user))


@router.post("/vacancies/{vacancy_id}/criteria", response_model=CriteriaOut)
def extract_criteria(
    vacancy_id: str,
    db: SessionDep,
    current_user: CurrentUser,
    engine: AffinityEngine = Depends(get_analysis_engine),
) -> Any:
    vacancy = _owned_vacancy(vacancy_id, db, current_user)
    try:
        criteria = engine.extract_criteria(vacancy.title, vacancy.description, vacancy.requirements)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (LLMProviderError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="No fue posible extraer criterios con el LLM.") from exc
    store_criteria(vacancy, criteria, "LLM")
    invalidate_analyses(db, vacancy.id)
    db.commit()
    db.refresh(vacancy)
    return _criteria_response(vacancy)


@router.put("/vacancies/{vacancy_id}/criteria", response_model=CriteriaOut)
def update_criteria(
    vacancy_id: str,
    criteria_in: VacancyCriteria,
    db: SessionDep,
    current_user: CurrentUser,
) -> Any:
    vacancy = _owned_vacancy(vacancy_id, db, current_user)
    criteria = normalize_weights(criteria_in)
    store_criteria(vacancy, criteria, "HUMAN")
    invalidate_analyses(db, vacancy.id)
    db.commit()
    db.refresh(vacancy)
    return _criteria_response(vacancy)


@router.post(
    "/vacancies/{vacancy_id}/run",
    response_model=AnalysisRunOut,
    status_code=status.HTTP_200_OK,
)
def run_analysis(
    vacancy_id: str,
    db: SessionDep,
    current_user: CurrentUser,
    engine: AffinityEngine = Depends(get_analysis_engine),
) -> Any:
    vacancy = _owned_vacancy(vacancy_id, db, current_user)
    criteria = stored_criteria(vacancy)
    if criteria is None:
        try:
            criteria = engine.extract_criteria(vacancy.title, vacancy.description, vacancy.requirements)
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (LLMProviderError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="No fue posible extraer criterios con el LLM.") from exc
        store_criteria(vacancy, criteria, "LLM")
        db.commit()

    applications = db.query(Application).filter(Application.vacancy_id == vacancy.id).all()
    results = []
    analyzed = 0
    failed = 0
    for application in applications:
        try:
            analyze_application(db, application, criteria, engine)
            analyzed += 1
        except Exception:
            failed += 1
        current = db.get(Application, application.id)
        results.append(AnalysisResultOut(
            application_id=current.id,
            score=current.ai_score,
            analysis_status=current.analysis_status,
            analyzed_at=current.analyzed_at,
            error=current.analysis_error if current.analysis_status == "FAILED" else None,
        ))
    return AnalysisRunOut(
        vacancy_id=vacancy.id,
        analyzed=analyzed,
        failed=failed,
        results=results,
    )
