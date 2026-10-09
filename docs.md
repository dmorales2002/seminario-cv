Deploy Result

┌──────────┬────────────────────────────────────────┬──────────────────────────────────────────┐
│ │ Backend │ Frontend │
├──────────┼────────────────────────────────────────┼──────────────────────────────────────────┤
│ URL │ https://backend-three-fawn-30.vercel.a │ https://frontend-sigma-peach-83.vercel.a │
│ │ pp │ pp │
├──────────┼────────────────────────────────────────┼──────────────────────────────────────────┤
│ Estado │ READY │ READY │
├──────────┼────────────────────────────────────────┼──────────────────────────────────────────┤
│ Framewor │ FastAPI (Python 3.12) │ React/Vite │
│ k │ │ │
├──────────┼────────────────────────────────────────┼──────────────────────────────────────────┤
│ BD │ Neon PostgreSQL │ — │
└──────────┴────────────────────────────────────────┴──────────────────────────────────────────┘

---

Advertencia importante: subida de CVs

El directorio uploads/ no persiste en Vercel serverless. Si los candidatos suben CVs, los archivos
se perderán entre requests. Para resolverlo en el futuro necesitarás migrar el almacenamiento a
Vercel Blob o Cloudflare R2. Por ahora el resto de la API funciona correctamente.

✻ Worked for 6m 5s · 1 shell still running

⏺ Background command "Get runtime logs from deployment" completed (exit code 0)

Read 1 file (ctrl+o to expand)

⏺ El .gitignore ya está bien configurado — .env en la raíz está ignorado (línea 12), así que las
credenciales de Neon y OpenAI no se van a commitear al repo.

Las carpetas .vercel/ que se crearon en backend/ y frontend/ también fueron añadidas
automáticamente a sus respectivos .gitignore por el CLI durante el vercel link.

Todo está en orden:

┌───────────────────────────────────┬─────────────────────────┐
│ Archivo │ Estado en git │
├───────────────────────────────────┼─────────────────────────┤
│ .env (raíz con credenciales Neon) │ Ignorado ✓ │
├───────────────────────────────────┼─────────────────────────┤
│ backend/.env │ Ignorado ✓ │
├───────────────────────────────────┼─────────────────────────┤
│ frontend/.env │ Ignorado ✓ │
├───────────────────────────────────┼─────────────────────────┤
│ backend/.vercel/ │ Ignorado ✓ (por el CLI) │
├───────────────────────────────────┼─────────────────────────┤
│ frontend/.vercel/ │ Ignorado ✓ (por el CLI) │
└───────────────────────────────────┴─────────────────────────┘

Los archivos que sí se commitearán y son seguros:

- backend/vercel.json
- backend/api/index.py
- backend/.vercelignore
- frontend/vercel.json
