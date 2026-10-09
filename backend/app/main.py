from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import analysis, auth, users, vacancies, applications
from app.core.config import settings

app = FastAPI(
    title="MVP Preselección de Candidatos",
    description="API para automatizar la preselección de candidatos usando LLM.",
    version="0.4.0",
)

# CORS — en producción restringir allow_origins a dominios específicos
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(users.router,        prefix="/api/v1/users",        tags=["Users"])
app.include_router(vacancies.router,    prefix="/api/v1/vacancies",    tags=["Vacancies"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["Applications"])
app.include_router(analysis.router,     prefix="/api/v1/analysis",     tags=["Analysis"])


@app.get("/", tags=["Health"])
def read_root():
    return {"status": "ok", "message": "MVP API v0.4.0 is running"}
