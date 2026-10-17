# Backend — MVP de preselección de candidatos

## Configuración

1. Copiar `.env.example` a `.env`.
2. Definir en `.env` una `SECRET_KEY` aleatoria de al menos 32 caracteres (es obligatoria), `OPENAI_API_KEY` y, si se van a registrar reclutadores, `RECRUITER_INVITE_CODE`. Sin ese código solo se registran candidatos.
3. Iniciar PostgreSQL desde la raíz: `docker compose up -d`.
4. Aplicar migraciones: `alembic upgrade head`.
5. Iniciar la API: `uvicorn app.main:app --reload`.

El modelo predeterminado es el snapshot `gpt-4o-mini-2024-07-18`. Puede cambiarse con
`OPENAI_MODEL`. Las solicitudes al proveedor usan Structured Outputs, temperatura cero,
reintentos acotados y `store=False`.

## Almacenamiento y análisis por lotes

Los currículums originales se guardan en la base de datos y solo se entregan por la API autenticada al
candidato que los cargó y al reclutador de la vacante; no existe un enlace público. `POST .../run`
analiza por tiempo (`ANALYSIS_TIME_BUDGET_SECONDS`, 40 s por solicitud) y devuelve `pending` y `complete`;
el cliente repite la solicitud hasta que no queden postulaciones pendientes.

## Flujo de análisis

1. `POST /api/v1/analysis/vacancies/{id}/criteria` extrae habilidades y actividades.
2. `PUT /api/v1/analysis/vacancies/{id}/criteria` permite al reclutador corregir nombres y pesos.
3. `POST /api/v1/analysis/vacancies/{id}/run` analiza las postulaciones y persiste el ranking.
4. `GET /api/v1/applications/{id}` devuelve el ranking y el desglose de evidencias.

El LLM extrae conceptos y propone equivalencias semánticas. Python normaliza los pesos y
calcula el puntaje. Educación, títulos y duración de experiencia se excluyen de los prompts,
los esquemas y la fórmula. Cada coincidencia debe apuntar a una cita comprobada dentro del
texto extraído del CV. Una huella de las entradas evita recalcular casos sin cambios.

## Pruebas

Pruebas unitarias:

```powershell
python -m unittest discover -s tests -v
```

Prueba de integración con PostgreSQL y proveedor simulado:

```powershell
$env:RUN_DB_INTEGRATION='1'
python -m unittest tests.test_phase4_api_integration -v
```

La prueba de integración no llama a OpenAI ni consume créditos.
