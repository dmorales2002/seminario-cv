# Expediente — MVP

Sistema web de apoyo a la preselección de candidatos por afinidad de habilidades y
actividades. El motor ordena y explica; el reclutador conserva siempre la decisión.

## Ejecutar localmente

Terminal 1 — PostgreSQL y backend:

```powershell
docker compose up -d
cd backend
.\venv\Scripts\alembic.exe upgrade head
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Terminal 2 — frontend:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Abrir `http://127.0.0.1:5173`. La documentación interactiva de la API está en
`http://127.0.0.1:8000/docs`.

## Verificación

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests -v

cd ..\frontend
npm test
npm run build
```

Para la prueba integral del motor con PostgreSQL:

```powershell
cd backend
$env:RUN_DB_INTEGRATION='1'
.\venv\Scripts\python.exe -m unittest tests.test_phase4_api_integration -v
```
