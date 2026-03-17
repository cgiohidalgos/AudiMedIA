# Historial de Cambios - Despliegue Producción (2026-03-17)

## 1. Infraestructura - Nginx Reverse Proxy

- Configurado **nginx** como reverse proxy en Docker para servir dos dominios en el mismo servidor:
  - `https://audimedia.co/` → frontend + backend AudiMedIA
  - `https://akila.work/` → app ADAT (contenedor `adat_app:5002`)
- Archivo: `nginx/default.conf` con 4 server blocks (HTTP→HTTPS redirect + HTTPS proxy por dominio)
- Nginx conectado a ambas redes Docker (`default` + `testct_adat_network`)
- Límite de subida aumentado a 200MB (`client_max_body_size 200m`)

## 2. SSL / HTTPS

- Certificado SSL obtenido para `akila.work` via **certbot** (método webroot)
- Certificado válido hasta 2026-06-15
- Renovación automática configurada con **systemd timer** (`certbot-renew.timer`) — ejecuta 2 veces al día y recarga nginx

## 3. Frontend - Modo Producción

- Cambiado de `npm run dev` (Vite dev server) a **build estático de producción** (`npm run build`)
- Nginx sirve los archivos estáticos desde `/app/dist` — reducción de carga de ~12s a <1s
- Script `deploy-frontend.sh` creado para rebuilds rápidos

## 4. Frontend - Correcciones

- **403 Forbidden**: Agregado `allowedHosts` en `vite.config.ts` para `audimedia.co`
- **CORS localhost**: Cambiado `VITE_API_URL` de `http://localhost:8000/api/v1` a `/api/v1` (relativo)
- **Caracteres UTF-8 corruptos**: Corregidos en `UploadScreen.tsx` y `ChatPanel.tsx` (Ã¡→á, Ã­→í, etc.)
- **Branding**: Reemplazado "Lovable" por "Audi Med IA" en `index.html` (title, meta tags, favicon)
- **Logo**: Agregado `logo.png` como favicon e imagen del proyecto

## 5. Backend - Procesamiento IA

- **Proveedor cambiado**: Cohere (lento, inestable) → **OpenAI gpt-4o-mini** (rápido, confiable)
- **Procesamiento paralelo**: Implementado `asyncio.gather` + `asyncio.Semaphore` para procesar múltiples lotes simultáneamente
  - `PARALLEL_BATCHES = 30` (antes 10)
  - `BATCH_SIZE = 3` (antes 5)
- **Retry + fallback**: Reintentos automáticos con fallback a OpenAI si Cohere falla
- **Velocidad**: ~170 lotes procesados en ~2 minutos vs ~10+ minutos antes

## 6. Backend - Funcionalidades

- **Cancelar análisis**: Endpoint `DELETE /processing/{session_id}` + botón X en frontend
- **Recuperación de sesiones**: Al reiniciar backend, sesiones huérfanas en estado 'analizando' se reanudan automáticamente
- **Auto-navegación**: Al completar procesamiento, el frontend navega automáticamente a "Ver análisis"

## 7. Backend - Optimización de Consultas

- **Eliminado N+1** en endpoint de pacientes (`patients.py`): carga relaciones con `selectinload` en una sola query
- Optimizado `AppPage.tsx` para no hacer llamadas redundantes

## 8. Contexto de Procesamiento

- `ProcessingContext.tsx`: Verificación de autenticación antes de hacer polling
- Limpieza de sessionStorage cuando no hay token válido
- Skip de re-renders cuando el progreso no ha cambiado

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `docker-compose.yml` | Nginx service, redes, frontend producción |
| `nginx/default.conf` | Reverse proxy config (nuevo) |
| `deploy-frontend.sh` | Script de deploy frontend (nuevo) |
| `frontend/index.html` | Branding Audi Med IA, meta tags |
| `frontend/vite.config.ts` | allowedHosts |
| `frontend/src/components/AppNavbar.tsx` | Cancel button, auto-navigate |
| `frontend/src/components/ChatPanel.tsx` | Fix UTF-8 |
| `frontend/src/components/UploadScreen.tsx` | Fix UTF-8 |
| `frontend/src/contexts/ProcessingContext.tsx` | Auth guard, skip re-render |
| `frontend/src/lib/api.ts` | Cancel endpoint |
| `frontend/src/pages/AppPage.tsx` | Optimización queries |
| `backend/app/api/v1/endpoints/processing.py` | Parallel batches, cancel |
| `backend/app/api/v1/endpoints/patients.py` | selectinload N+1 fix |
| `backend/app/main.py` | Session recovery on startup |
| `backend/app/models/audit.py` | Model updates |
| `backend/app/services/ai/extractor.py` | OpenAI, parallel, retry |
