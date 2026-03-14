"""
Servicio de extracción estructurada de variables clínicas usando LLM.
"""
import asyncio
import json
import logging
import re
from typing import Any, Callable, Optional
from openai import AsyncOpenAI
import random
from app.core.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Retry utilitario para llamadas a OpenAI
async def retry_with_backoff(func, *args, max_retries=5, base_delay=2, max_delay=32, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Manejar solo errores 429 o de red/transitorios
            if hasattr(e, 'status_code') and e.status_code == 429:
                wait = min(base_delay * 2 ** (attempt - 1), max_delay)
                wait = wait * (0.8 + 0.4 * random.random())  # Jitter
                logger.warning(f"⏳ Límite de tasa alcanzado (429). Reintentando en {wait:.1f}s (intento {attempt}/{max_retries})...")
                await asyncio.sleep(wait)
            elif 'rate limit' in str(e).lower() or '429' in str(e):
                wait = min(base_delay * 2 ** (attempt - 1), max_delay)
                wait = wait * (0.8 + 0.4 * random.random())
                logger.warning(f"⏳ Rate limit detectado. Reintentando en {wait:.1f}s (intento {attempt}/{max_retries})...")
                await asyncio.sleep(wait)
            elif attempt == max_retries:
                logger.error(f"❌ Error persistente tras {max_retries} reintentos: {type(e).__name__}: {str(e)}")
                raise
            else:
                logger.warning(f"⚠️ Error transitorio: {type(e).__name__}: {str(e)}. Reintentando...")
                await asyncio.sleep(2)
    raise RuntimeError("No se pudo completar la llamada tras varios reintentos")

EXTRACTION_PROMPT = """Eres un experto en auditoría médica colombiana. Analiza la siguiente historia clínica
(ya anonimizada) y extrae TODAS las variables clínicas en formato JSON estricto.

IMPORTANTE: Los nombres de pacientes YA FUERON ANONIMIZADOS (no intentes extraerlos).

Historia clínica:
{text}

Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:
{{
  "edad": null,
  "sexo": null,
  "cama": null,
  "diagnostico_principal": null,
  "codigo_cie10": null,
  "diagnosticos_secundarios": [
    {{"codigo": "CIE10", "descripcion": "Descripción de la comorbilidad"}}
  ],
  "fecha_ingreso": null,
  "dias_hospitalizacion": null,
  "dias_esperados": null,
  "fecha_egreso": null,
  "medicamentos": [
    {{"nombre": "", "dosis": "", "frecuencia": ""}}
  ],
  "antecedentes": {{
    "patologicos": [],
    "quirurgicos": [],
    "farmacologicos": [],
    "familiares": []
  }},
  "estudios_solicitados": [
    {{"nombre": "", "fecha": "", "resultado_disponible": false, "justificacion": ""}}
  ],
  "procedimientos": [
    {{"nombre": "", "fecha": "", "justificacion": ""}}
  ],
  "evoluciones": [
    {{"fecha": "", "resumen": ""}}
  ]
}}

INSTRUCCIONES ESPECÍFICAS:
- diagnosticos_secundarios: DEBE incluir código CIE-10 y descripción para cada uno
- estudios_solicitados: Incluir paraclínicos e imágenes con su justificación clínica
- procedimientos: Extraer intervenciones quirúrgicas o procedimientos con fecha y justificación
- dias_hospitalizacion: Calcular diferencia entre fecha_ingreso y fecha actual/egreso (use la fecha de egreso si está disponible)
- fecha_egreso: Buscar en el texto la última fecha dentro del bloque "RESUMEN DEL PLAN TERAPEUTICO" y úsala como fecha de egreso; si no encuentras ninguno, dejar null.
- dias_esperados: Buscar en el texto si mencionan tiempo esperado de hospitalización
- antecedentes.farmacologicos: Medicación previa o alergias conocidas
- Usa null para valores no encontrados, [] para arrays vacíos
- Solo devuelve JSON, sin texto adicional"""

SUMMARY_PROMPT = """Eres un asistente experto en historias clínicas. Resume de manera muy concisa la información relevante de la siguiente historia clínica, manteniendo los datos clínicos importantes (fechas, diagnósticos, procedimientos, medicamentos, hallazgos, etc.).

El objetivo es reducir el texto a lo esencial para que otro modelo pueda extraer variables clínicas.

Historia clínica:
{text}

Devuelve un resumen en texto libre, sin introducir información nueva ni eliminar datos críticos.
"""


def _try_fix_json_string(s: str) -> str:
    """Intenta corregir respuestas JSON levemente malformadas."""
    # Reemplazar valores de Python a JSON
    s = s.replace("None", "null").replace("True", "true").replace("False", "false")
    # Quitar comas finales antes de } o ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # Reemplazar comillas simples por dobles si parece JSON
    if "'" in s and '"' not in s:
        s = s.replace("'", '"')
    return s


def _merge_clinical_dicts(base: dict, other: dict) -> dict:
    """Une dos diccionarios de variables clínicas.
    - para cadenas, conserva el valor de `base` si no es `None`.
    - para listas, concatena elementos únicos.
    - para sub-diccionarios, aplica recursivamente.
    """
    if not base:
        return other.copy()
    merged = base.copy()
    for k, v in other.items():
        if v is None:
            continue
        if isinstance(v, list):
            existing = merged.get(k) or []
            # evitar duplicados sencillos
            items = existing[:] if isinstance(existing, list) else []
            for item in v:
                if item not in items:
                    items.append(item)
            merged[k] = items
        elif isinstance(v, dict):
            merged[k] = _merge_clinical_dicts(merged.get(k, {}), v)
        else:
            if merged.get(k) is None:
                merged[k] = v
    return merged


async def extract_clinical_variables(text: str, progress_callback: Optional[Callable[[float], Any]] = None) -> dict:
    """Extrae variables clínicas estructuradas del texto de la historia clínica.

    Divide el texto en fragmentos y los procesa en PARALELO para reducir
    la latencia total. Combina los resultados parciales en un único diccionario.

    Para reducir el gasto de tokens en textos muy largos, puede generarse un
    resumen previo usando el mismo modelo, y luego extraer sobre ese resumen.
    """
    try:
        logger.info(f"🔍 Extrayendo variables clínicas (texto: {len(text)} chars)...")
        logger.info(f"🔑 API Key configurada: {settings.OPENAI_API_KEY[:20]}...")
        logger.info(f"🤖 Modelo: {settings.LLM_MODEL}")

        # Fragmentos grandes para minimizar el número de llamadas a la API
        max_chunk = 30000
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_chunk, len(text))
            if end < len(text):
                nl = text.rfind("\n", start, end)
                if nl > start:
                    end = nl
            chunks.append(text[start:end])
            start = end
        logger.info(f"🔍 Texto dividido en {len(chunks)} fragmento(s) para extracción (paralelo)")

        async def _call_chunk(chunk: str, idx: int) -> dict:
            logger.info(f"🔍 Fragmento {idx}/{len(chunks)} iniciando (size {len(chunk)})")
            try:
                response = await client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": "Eres un auditor médico experto en normativa colombiana (CIE10, CUPS, Ley 1438)."},
                        {"role": "user", "content": EXTRACTION_PROMPT.format(text=chunk)},
                    ],
                    temperature=0,
                    response_format={"type": "json_object"},
                )
                result = json.loads(response.choices[0].message.content)
                logger.info(f"  ✅ Fragmento {idx} completado exitosamente")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"  ❌ Fragmento {idx} - Error JSON: {e}")
                logger.error(f"  📜 Respuesta malformada: {response.choices[0].message.content[:200]}...")
                return {"error": f"JSON malformado en fragmento {idx}: {str(e)}"}
            except Exception as e:
                logger.error(f"  ❌ Fragmento {idx} - Error OpenAI: {type(e).__name__}: {str(e)}")
                if hasattr(e, 'response'):
                    logger.error(f"  📜 Respuesta HTTP: {getattr(e.response, 'status_code', 'N/A')}")
                return {"error": f"Error en fragmento {idx}: {str(e)}"}

        # Si el texto es muy grande, primero resumir para gastar menos tokens.
        text_to_process = text
        if settings.LLM_USE_SUMMARIZATION and len(text) > settings.LLM_SUMMARIZE_THRESHOLD_CHARS:
            logger.info(
                f"✂️ Texto muy grande ({len(text)} chars). Generando resumen antes de extraer variables..."
            )

            async def _summarize_chunk(chunk: str, idx: int) -> str:
                logger.info(f"🔎 Resumen fragmento {idx} (size {len(chunk)})")
                async def call():
                    return await client.chat.completions.create(
                        model=settings.LLM_MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": "Eres un asistente experto en historias clínicas. Resume la información relevante de forma concisa.",
                            },
                            {"role": "user", "content": SUMMARY_PROMPT.format(text=chunk)},
                        ],
                        temperature=0,
                        max_tokens=settings.LLM_SUMMARIZE_MAX_TOKENS,
                    )
                start = asyncio.get_event_loop().time()
                response = await retry_with_backoff(call)
                duration = asyncio.get_event_loop().time() - start
                # Log detalles de la llamada LLM
                try:
                    usage = getattr(response, 'usage', None) or (response.get('usage') if isinstance(response, dict) else None)
                except Exception:
                    usage = None
                logger.debug(f"  ⏱️ Resumen LLM fragmento {idx} duracion={duration:.2f}s model={settings.LLM_MODEL} prompt_chars={len(chunk)} usage={usage}")
                logger.debug(f"  🔁 Respuesta bruta (trunc): {str(response)[:1000]}")
                return (response.choices[0].message.content or "").strip()

            summarize_chunks = _chunk_text(text, settings.LLM_SUMMARIZE_CHUNK_SIZE)
            logger.info(f"🔍 Texto dividido en {len(summarize_chunks)} fragmento(s) para resumir (paralelo)")
            summaries = await asyncio.gather(
                *[_summarize_chunk(c, i + 1) for i, c in enumerate(summarize_chunks)]
            )
            text_to_process = "\n\n".join(f"[Resumen {i+1}]\n{s}" for i, s in enumerate(summaries))
            logger.info(f"✅ Resumen generado ({len(text_to_process)} chars). Continuando con extracción.")


        # Fragmentos para extracción final (secuencial y robusto)
        max_chunk = settings.LLM_SUMMARIZE_CHUNK_SIZE
        chunks = _chunk_text(text_to_process, max_chunk)
        logger.info(f"🔍 Texto dividido en {len(chunks)} fragmento(s) para extracción (secuencial)")

        combined: dict = {}
        errores: list = []

        # Limitar concurrencia de fragmentos
        MAX_CONCURRENT_CHUNKS = 2  # Puedes ajustar este valor según pruebas
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHUNKS)


        async def process_chunk(idx, chunk):
            async with semaphore:
                logger.info(f"🔍 Fragmento {idx}/{len(chunks)} iniciando (size {len(chunk)})")
                try:
                    async def call():
                        return await client.chat.completions.create(
                            model=settings.LLM_MODEL,
                            messages=[
                                {"role": "system", "content": "Eres un auditor médico experto en normativa colombiana (CIE10, CUPS, Ley 1438)."},
                                {"role": "user", "content": EXTRACTION_PROMPT.format(text=chunk)},
                            ],
                            temperature=0,
                            max_tokens=settings.LLM_MAX_TOKENS,
                            response_format={"type": "json_object"},
                        )
                    start = asyncio.get_event_loop().time()
                    response = await retry_with_backoff(call)
                    duration = asyncio.get_event_loop().time() - start
                    # registrar metadatos de la llamada
                    try:
                        usage = getattr(response, 'usage', None) or (response.get('usage') if isinstance(response, dict) else None)
                    except Exception:
                        usage = None
                    logger.info(f"  ⏱️ Fragmento {idx} LLM duracion={duration:.2f}s model={settings.LLM_MODEL} prompt_chars={len(chunk)} usage={usage}")
                    logger.debug(f"  🔁 Respuesta bruta fragmento {idx} (trunc): {str(response)[:1500]}")
                    content = response.choices[0].message.content
                    try:
                        result = json.loads(content)
                        logger.info(f"  ✅ Fragmento {idx} completado")
                        if progress_callback and len(chunks) > 0:
                            pct = idx / len(chunks)
                            logger.debug(f"🔁 progress_callback idx={idx} pct={pct:.3f}")
                            try:
                                await progress_callback(pct)
                            except Exception as e:
                                logger.warning(f"⚠️ progress_callback fallo: {e}")
                        return (idx, result, None)
                    except json.JSONDecodeError as jde:
                        # Intentar limpiar el string y reintentar
                        logger.error(f"❌ JSONDecodeError en fragmento {idx}: {str(jde)}. Respuesta bruta: {content[:1000]!r}...")
                        content_fixed = _try_fix_json_string(content)
                        try:
                            result = json.loads(content_fixed)
                            logger.info(f"  ⚠️ Fragmento {idx} recuperado tras limpieza de JSON")
                            if progress_callback and len(chunks) > 0:
                                pct = idx / len(chunks)
                                logger.debug(f"🔁 progress_callback idx={idx} pct={pct:.3f}")
                                try:
                                    await progress_callback(pct)
                                except Exception as e:
                                    logger.warning(f"⚠️ progress_callback fallo: {e}")
                            return (idx, result, None)
                        except Exception as e2:
                            logger.error(f"❌ Fallo al limpiar JSON en fragmento {idx}: {str(e2)}")
                        # Extraer el bloque JSON entre el primer '{' y el último '}' y volver a intentar
                        if isinstance(content, str) and '{' in content and '}' in content:
                            start = content.find('{')
                            end = content.rfind('}')
                            fixed = content[start:end+1]
                            fixed = _try_fix_json_string(fixed)
                            try:
                                result = json.loads(fixed)
                                logger.info(f"  ⚠️ Fragmento {idx} recuperado tras limpieza de JSON (segundo intento)")
                                if progress_callback and len(chunks) > 0:
                                    pct = idx / len(chunks)
                                    logger.debug(f"🔁 progress_callback idx={idx} pct={pct:.3f}")
                                    try:
                                        await progress_callback(pct)
                                    except Exception as e:
                                        logger.warning(f"⚠️ progress_callback fallo: {e}")
                                return (idx, result, None)
                            except Exception as e3:
                                logger.error(f"❌ Fallo al extraer JSON en fragmento {idx}: {str(e3)}")
                        return (idx, None, {"fragmento": idx, "error": f"JSONDecodeError: {str(jde)}", "size": len(chunk), "respuesta": content[:2000] if isinstance(content, str) else str(content)})
                except Exception as e:
                    logger.error(f"❌ Error en fragmento {idx}: {type(e).__name__}: {str(e)}")
                    return (idx, None, {"fragmento": idx, "error": str(e), "size": len(chunk)})

        results = await asyncio.gather(
            *[process_chunk(idx, chunk) for idx, chunk in enumerate(chunks, 1)]
        )

        for idx, result, error in results:
            if result is not None:
                combined = _merge_clinical_dicts(combined, result)
            if error is not None:
                errores.append(error)

        logger.info(f"✅ Extracción completa, campos consolidados: {len(combined)}")
        if errores:
            logger.error(f"❌ Fragmentos fallidos: {json.dumps(errores, ensure_ascii=False, indent=2)}")
            combined["errores_fragmentos"] = errores
        logger.info(f"📊 Datos extraídos finales: {json.dumps(combined, ensure_ascii=False, indent=2)}")
        return combined

    except Exception as e:
        logger.error(f"❌ ERROR GLOBAL en extracción de variables: {type(e).__name__}: {str(e)}")
        if 'RateLimitError' in str(type(e)) or 'insufficient_quota' in str(e).lower():
            logger.error(f"💰 PROBLEMA DE CUOTA: La API key no tiene créditos suficientes")
            logger.error(f"💰 Solución: Recarga créditos en platform.openai.com/settings/billing")
        logger.exception("Traceback completo:")
        return {"error": str(e)}
