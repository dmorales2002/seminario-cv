"""
Endpoint de postulación: valida y extrae CVs (PDF/DOCX), persiste el
archivo original y registra la postulación para su posterior análisis.
"""
import os
import uuid
from typing import Any
from fastapi import APIRouter, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.api.deps import SessionDep, CurrentUser
from app.models.vacancy import Vacancy, VacancyStatus
from app.models.resume import Resume
from app.models.application import Application, ApplicationStatus
from app.models.user import UserRole
from app.schemas.application import ApplicationOut, ApplicationWithCandidateOut, ApplicationStatusUpdate
from app.services.extractor import extract_text
from app.core.config import settings

router = APIRouter()

# ── Configuración ──────────────────────────────────────────────────────────────
UPLOAD_DIR = str(settings.UPLOAD_DIR)
MAX_FILE_SIZE_MB = settings.MAX_CV_SIZE_MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

FILE_SIGNATURES = {
    "pdf": b"%PDF-",
    "docx": b"PK\x03\x04",
}
DOWNLOAD_MEDIA_TYPES = {file_type: mime for mime, file_type in ALLOWED_MIME_TYPES.items()}


def validate_cv_content(file_bytes: bytes, file_type: str) -> None:
    """Validate size and magic bytes; MIME headers alone are user-controlled."""
    if not file_bytes:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo excede el límite de {MAX_FILE_SIZE_MB}MB.",
        )
    if not file_bytes.startswith(FILE_SIGNATURES[file_type]):
        raise HTTPException(
            status_code=415,
            detail="El contenido del archivo no corresponde al formato declarado.",
        )


def _get_vacancy_or_404(vacancy_id: str, db: Session) -> Vacancy:
    vacancy = db.query(Vacancy).filter(Vacancy.id == vacancy_id).first()
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacante no encontrada.")
    return vacancy


# ── POST /applications/{vacancy_id} ──────────────────────────────────────────
@router.post("/{vacancy_id}", response_model=ApplicationOut, status_code=status.HTTP_202_ACCEPTED)
async def apply_to_vacancy(
    vacancy_id: str,
    db: SessionDep,
    current_user: CurrentUser,
    cv_file: UploadFile = File(..., description="CV en formato PDF o DOCX (máx. 5MB)"),
) -> Any:
    """
    El candidato se postula a una vacante enviando su CV.
    
    - Valida que el usuario sea CANDIDATE.
    - Valida formato y tamaño del archivo.
    - Guarda el archivo en /uploads.
    - Comprueba que el documento sea legible y contenga texto seleccionable.
    - Crea la fila en `resumes` y `applications` (status=PENDING, score=None).
    - Responde HTTP 202 cuando la postulación quedó registrada.
    """
    # 1. Verificar rol
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(status_code=403, detail="Solo los candidatos pueden postularse.")

    # 2. Verificar que la vacante exista y esté abierta
    vacancy = _get_vacancy_or_404(vacancy_id, db)
    if vacancy.status != VacancyStatus.OPEN:
        raise HTTPException(status_code=400, detail="Esta vacante está cerrada.")

    # 3. Verificar que no se haya postulado ya
    existing = (
        db.query(Application)
        .filter(Application.vacancy_id == vacancy_id, Application.candidate_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Ya te has postulado a esta vacante.")

    # 4. Validar tipo MIME
    if cv_file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Formato no soportado: '{cv_file.content_type}'. Solo se aceptan PDF y DOCX.",
        )
    file_type = ALLOWED_MIME_TYPES[cv_file.content_type]

    # 5. Leer y validar tamaño
    file_bytes = await cv_file.read()
    validate_cv_content(file_bytes, file_type)

    # Validar el documento antes de persistir la postulación. De este modo un
    # archivo corrupto o sin texto seleccionable produce una respuesta útil.
    try:
        raw_text = await run_in_threadpool(extract_text, file_bytes, file_type)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="No se pudo leer el documento. Verifica que sea un PDF o DOCX válido.",
        ) from exc
    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="El documento no contiene texto seleccionable.",
        )

    # 6. Guardar archivo en disco con nombre único
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_uuid = str(uuid.uuid4())
    safe_filename = f"{file_uuid}.{file_type}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # 7. Crear registro en `resumes` con el texto ya validado
    resume = Resume(
        candidate_id=current_user.id,
        file_path=file_path,
        file_type=file_type,
        raw_text=raw_text,
    )
    try:
        db.add(resume)
        db.flush()  # Para obtener el ID sin cerrar la transacción

        # 8. Crear registro en `applications` (PENDING, score=None)
        application = Application(
            vacancy_id=vacancy_id,
            candidate_id=current_user.id,
            resume_id=resume.id,
            status=ApplicationStatus.PENDING,
            ai_score=None,
            ai_evidence=None,
        )
        db.add(application)
        db.commit()
        db.refresh(resume)
        db.refresh(application)
    except IntegrityError:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=409, detail="Ya te has postulado a esta vacante.")
    except Exception:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    return application


# ── GET /applications/{vacancy_id} — Panel del Reclutador ────────────────────
@router.get("/{vacancy_id}", response_model=list[ApplicationWithCandidateOut])
def get_applications_for_vacancy(
    vacancy_id: str,
    db: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Retorna el ranking de candidatos para una vacante, ordenados por ai_score DESC.
    Solo accesible por el reclutador creador de esa vacante.
    """
    if current_user.role != UserRole.RECRUITER:
        raise HTTPException(status_code=403, detail="Solo los reclutadores pueden ver las postulaciones.")

    vacancy = _get_vacancy_or_404(vacancy_id, db)
    if str(vacancy.recruiter_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta vacante.")

    applications = (
        db.query(Application)
        .filter(Application.vacancy_id == vacancy_id)
        .order_by(Application.ai_score.desc().nulls_last())
        .all()
    )

    result = []
    for app in applications:
        candidate = app.candidate
        result.append(
            ApplicationWithCandidateOut(
                id=app.id,
                vacancy_id=app.vacancy_id,
                candidate_id=app.candidate_id,
                resume_id=app.resume_id,
                ai_score=app.ai_score,
                ai_evidence=app.ai_evidence,
                analysis_status=app.analysis_status,
                analysis_error=app.analysis_error,
                analyzed_at=app.analyzed_at,
                analyzer_version=app.analyzer_version,
                status=app.status,
                applied_at=app.applied_at,
                candidate_name=candidate.full_name if candidate else None,
                candidate_email=candidate.email if candidate else None,
            )
        )
    return result


# ── PATCH /applications/{vacancy_id}/{application_id} — Decisión del Reclutador
@router.patch("/{vacancy_id}/{application_id}", response_model=ApplicationOut)
def update_application_status(
    vacancy_id: str,
    application_id: str,
    status_in: ApplicationStatusUpdate,
    db: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    El reclutador actualiza el estado de una postulación a APPROVED o REJECTED.
    Este es el paso Human-in-the-loop: el sistema no descarta automáticamente.
    """
    if current_user.role != UserRole.RECRUITER:
        raise HTTPException(status_code=403, detail="Solo los reclutadores pueden actualizar postulaciones.")

    vacancy = _get_vacancy_or_404(vacancy_id, db)
    if str(vacancy.recruiter_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta vacante.")

    application = (
        db.query(Application)
        .filter(Application.id == application_id, Application.vacancy_id == vacancy_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada.")

    if status_in.status == ApplicationStatus.PENDING:
        raise HTTPException(status_code=422, detail="La decisión debe ser APPROVED o REJECTED.")

    application.status = status_in.status
    db.commit()
    db.refresh(application)
    return application


@router.get("/{vacancy_id}/{application_id}/resume", response_class=FileResponse)
def download_application_resume(
    vacancy_id: str,
    application_id: str,
    db: SessionDep,
    current_user: CurrentUser,
) -> FileResponse:
    """Entrega el CV original solo al candidato propietario o al reclutador de la vacante."""
    application = (
        db.query(Application)
        .filter(Application.id == application_id, Application.vacancy_id == vacancy_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Postulación no encontrada.")
    vacancy = _get_vacancy_or_404(vacancy_id, db)
    owns_application = str(application.candidate_id) == str(current_user.id)
    owns_vacancy = str(vacancy.recruiter_id) == str(current_user.id)
    if not (owns_application or owns_vacancy):
        raise HTTPException(status_code=403, detail="No tienes acceso a este currículum.")
    file_path = application.resume.file_path
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="El archivo original ya no está disponible.")
    return FileResponse(
        path=file_path,
        media_type=DOWNLOAD_MEDIA_TYPES[application.resume.file_type],
        filename=f"curriculum-{application.candidate_id}.{application.resume.file_type}",
    )


# ── GET /applications/my — Candidato: ver mis postulaciones ──────────────────
@router.get("/my/list", response_model=list[ApplicationOut])
def get_my_applications(db: SessionDep, current_user: CurrentUser) -> Any:
    """El candidato autenticado ve el estado de todas sus postulaciones."""
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(status_code=403, detail="Solo los candidatos pueden ver sus postulaciones.")

    applications = (
        db.query(Application)
        .filter(Application.candidate_id == current_user.id)
        .order_by(Application.applied_at.desc())
        .all()
    )
    return applications
