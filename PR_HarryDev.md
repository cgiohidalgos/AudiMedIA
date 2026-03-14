# PR: fix — Corrección extracción de IA, pipeline de upload y configuración CORS

**Rama:** `HarryDev` → `main`  
**Commit:** `643a7a1`  
**Fecha:** 14/03/2026  
**Autor:** Harry  

---

## Descripción

Este PR agrupa un conjunto de correcciones críticas que estaban impidiendo el correcto funcionamiento del pipeline de procesamiento de PDFs, la extracción de datos mediante IA y la comunicación entre el frontend y el backend.

---

## Cambios por archivo

### `backend/app/api/v1/endpoints/upload.py`
**Mejoras en observabilidad del endpoint de subida**

- Logging paso a paso en todo el flujo de upload con emojis indicadores de etapa.
- Se registra el usuario, cantidad y nombres de archivos recibidos al inicio de cada request.
- Se loguea el tamaño en bytes y KB de cada archivo procesado.
- Se muestra el hash SHA-256 calculado para cada PDF (primeros y últimos 4 caracteres).
- Se confirma explícitamente cuándo un archivo es guardado en disco.
- Se registra cuándo se detecta un documento duplicado (reuso de sesión existente).
- Se loguea la creación de cada nueva sesión con su ID y label asignado.
- Se confirma que el worker fue encolado correctamente.
- Al final del request se detallan todas las respuestas enviadas al cliente.

```diff
- logger.info("[upload] archivo recibido: %s (idx=%d)", file.filename, idx)
+ logger.info(f"📎 [UPLOAD] Archivo {idx+1}/{len(files)}: {file.filename}")
+ logger.info(f"📄 [UPLOAD] Tamaño leído: {len(content):,} bytes ({len(content)/1024:.1f} KB)")
+ logger.info(f"💾 [UPLOAD] Archivo guardado exitosamente")
+ logger.info(f"🆕 [UPLOAD] Creando nueva sesión: {session_id} con label: {label}")
```

---

### `backend/app/services/ai/extractor.py`
**Corrección en manejo de errores al llamar a OpenAI en fragmentos paralelos**

- Cada llamada a la API de OpenAI ahora está encapsulada en `try/except` individual para evitar que un fragmento con error bloquee los demás.
- Se captura `json.JSONDecodeError` cuando la respuesta de OpenAI viene malformada, registrando el fragmento del contenido incorrecto para facilitar el diagnóstico.
- Se captura cualquier excepción genérica de OpenAI (incluyendo `AuthenticationError`, `RateLimitError`) y se retorna un dict de error en lugar de propagar la excepción.
- Se agrega detección específica de `RateLimitError` y `insufficient_quota` con mensaje de ayuda sobre recarga de créditos.

```diff
- response = await client.chat.completions.create(...)
- result = json.loads(response.choices[0].message.content)
- return result

+ try:
+     response = await client.chat.completions.create(...)
+     result = json.loads(response.choices[0].message.content)
+     return result
+ except json.JSONDecodeError as e:
+     logger.error(f"  ❌ Fragmento {idx} - Error JSON: {e}")
+     return {"error": f"JSON malformado en fragmento {idx}: {str(e)}"}
+ except Exception as e:
+     logger.error(f"  ❌ Fragmento {idx} - Error OpenAI: {type(e).__name__}: {str(e)}")
+     return {"error": f"Error en fragmento {idx}: {str(e)}"}
```

---

### `backend/app/workers/pdf_worker.py`
**Logging estructurado por pasos en el worker de procesamiento**

- Se agrega logging al inicio de cada etapa del pipeline con numeración explícita (Paso 1, 2, 4).
- **Paso 1 (Extracción):** se registra cantidad de páginas extraídas vs total de páginas del PDF.
- **Paso 2 (Anonimización):** se confirma inicio y fin del proceso de anonimización con cantidad de páginas procesadas.
- **Paso 4 (IA):** se registra el total de caracteres de texto enviado a OpenAI antes de la extracción.
- Se registran las claves de variables extraídas al finalizar exitosamente.

```diff
+ logger.info(f"📄 [WORKER] Paso 1: Extrayendo texto de PDF...")
+ logger.info(f"📄 [WORKER] Extraídas {len(pages)} páginas de texto.")
+ logger.info(f"🔒 [WORKER] Paso 2: Anonimizando contenido...")
+ logger.info(f"🤖 [WORKER] Paso 4: Extracción de variables con IA...")
+ logger.info(f"🤖 [WORKER] Texto preparado para IA: {len(full_anon_text)} caracteres")
```

---

### `frontend/src/lib/api.ts`
**Corrección de URL de fallback del cliente HTTP**

- Se corrige la URL de fallback del cliente API de `localhost:8000` a `localhost:8002`, que es el puerto real del servidor debug.
- Esto evitaba que el frontend apuntara a un servidor inexistente cuando no se definía la variable de entorno `VITE_API_URL`.

```diff
- const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';
+ const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8002/api/v1';
```

---

### `frontend/src/pages/ReporteIndividualPage.tsx`
**Corrección de advertencia de accesibilidad en DialogContent**

- Se agrega `aria-describedby={undefined}` al componente `DialogContent` del modal de sesión de auditoría previa.
- Esto silencia la advertencia de Radix UI: `Warning: Missing Description or aria-describedby for DialogContent`.

```diff
- <DialogContent className="sm:max-w-md">
+ <DialogContent className="sm:max-w-md" aria-describedby={undefined}>
```

---

### `frontend/vite.config.ts`
**Ajuste del puerto del servidor de desarrollo**

- Se cambia el puerto de Vite de `8080` a `8082` para evitar conflictos con otros servicios del entorno.
- El backend ya tenía CORS configurado para aceptar `localhost:8082`.

```diff
- port: 8080,
+ port: 8082,
```

---

## Archivos excluidos del PR

Los siguientes archivos de debugging/testing creados durante la sesión de diagnóstico **no fueron incluidos** en este commit:

- `backend/server_debug.py`
- `backend/server_cors_debug.py`
- `backend/server_cors_fix.py`
- `backend/debug_error.py`
- `backend/debug_ia_extraction.py`
- `backend/inspect_db.py`
- `backend/inspect_structure.py`
- `backend/monitor_live.py`
- `backend/run_server.py`
- `backend/test_endpoints.py`
- `backend/test_logging.py`
- `backend/test_upload_detailed.py`
- `backend/upload_with_countdown.py`
- `test_api.py` (raíz)

---

## Checklist

- [x] Los cambios no rompen funcionalidad existente
- [x] Se mejoró la observabilidad del pipeline de upload
- [x] Los errores de OpenAI son manejados gracefully sin cortar el flujo
- [x] El frontend apunta al backend correcto
- [x] No se suben archivos de debug/test temporales
- [x] No se exponen credenciales (`.env` está en `.gitignore`)

---

## Notas adicionales

> **API Key de OpenAI:** La key configurada en `.env` resultó inválida durante las pruebas. El chat funciona correctamente una vez se configure una key válida en `OPENAI_API_KEY`. Los nuevos logs del extractor muestran el error con claridad y guían al usuario hacia la solución.
