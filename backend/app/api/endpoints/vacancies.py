from typing import Any
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func
from app.api.deps import SessionDep, CurrentUser
from app.models.application import Application, ApplicationStatus
from app.models.vacancy import Vacancy, VacancyStatus
from app.models.user import UserRole
from app.schemas.vacancy import VacancyCreate, VacancyUpdate, VacancyOut, VacancySummaryOut
from app.services.analyzer import invalidate_analyses

router = APIRouter()


@router.post("/", response_model=VacancyOut, status_code=status.HTTP_201_CREATED)
def create_vacancy(
    *,
    db: SessionDep,
    vacancy_in: VacancyCreate,
    current_user: CurrentUser,
) -> Any:
    """Crea una nueva vacante. Solo accesible por RECRUITERS."""
    if current_user.role != UserRole.RECRUITER:
        raise HTTPException(status_code=403, detail="Solo los reclutadores pueden crear vacantes.")
    
    vacancy = Vacancy(
        recruiter_id=current_user.id,
        title=vacancy_in.title,
        description=vacancy_in.description,
        requirements=vacancy_in.requirements,
    )
    db.add(vacancy)
    db.commit()
    db.refresh(vacancy)
    return vacancy


@router.get("/", response_model=list[VacancyOut])
def list_open_vacancies(db: SessionDep, current_user: CurrentUser) -> Any:
    """Lista todas las vacantes abiertas. Accesible para CANDIDATES y RECRUITERS."""
    vacancies = db.query(Vacancy).filter(Vacancy.status == VacancyStatus.OPEN).all()
    return vacancies


@router.get("/my", response_model=list[VacancySummaryOut])
def list_my_vacancies(db: SessionDep, current_user: CurrentUser) -> Any:
    """Lista las vacantes creadas por el reclutador autenticado."""
    if current_user.role != UserRole.RECRUITER:
        raise HTTPException(status_code=403, detail="Solo los reclutadores tienen vacantes propias.")
    rows = (
        db.query(
            Vacancy,
            func.count(Application.id).label("application_count"),
            func.count(Application.id).filter(Application.status == ApplicationStatus.PENDING).label("pending_count"),
        )
        .outerjoin(Application, Application.vacancy_id == Vacancy.id)
        .filter(Vacancy.recruiter_id == current_user.id)
        .group_by(Vacancy.id)
        .order_by(Vacancy.created_at.desc())
        .all()
    )
    return [
        VacancySummaryOut.model_validate(vacancy).model_copy(
            update={"application_count": application_count, "pending_count": pending_count}
        )
        for vacancy, application_count, pending_count in rows
    ]


@router.get("/{vacancy_id}", response_model=VacancyOut)
def get_vacancy(vacancy_id: str, db: SessionDep, current_user: CurrentUser) -> Any:
    """Retorna el detalle de una vacante por su ID."""
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacante no encontrada.")
    return vacancy


@router.put("/{vacancy_id}", response_model=VacancyOut)
def update_vacancy(
    vacancy_id: str,
    vacancy_in: VacancyUpdate,
    db: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Actualiza una vacante. Solo el reclutador creador puede editarla."""
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacante no encontrada.")
    if str(vacancy.recruiter_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="No tienes permiso para editar esta vacante.")
    
    update_data = vacancy_in.model_dump(exclude_unset=True)
    criteria_changed = bool({"title", "description", "requirements"}.intersection(update_data))
    for field, value in update_data.items():
        setattr(vacancy, field, value)
    if criteria_changed:
        vacancy.ai_criteria = None
        vacancy.criteria_updated_at = None
        invalidate_analyses(db, vacancy.id)
    
    db.commit()
    db.refresh(vacancy)
    return vacancy


@router.delete("/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
def close_vacancy(vacancy_id: str, db: SessionDep, current_user: CurrentUser) -> None:
    """Cierra una vacante (cambia status a CLOSED). Solo el reclutador creador."""
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacante no encontrada.")
    if str(vacancy.recruiter_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="No tienes permiso para cerrar esta vacante.")
    
    vacancy.status = VacancyStatus.CLOSED
    db.commit()
