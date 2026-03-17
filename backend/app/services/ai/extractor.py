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
    s = s.replace("None", "null").replace("True", "true").replace("False", "false")
    s = re.sub(r",\s*([}\]])", r"\1", s)
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


def _extract_with_cohere(chunk: str, idx: int, max_retries: int = 2) -> dict:
    """Extracción síncrona con Cohere Command R. Se ejecuta en thread executor."""
    import cohere
    import time
    co = cohere.Client(api_key=settings.COHERE_API_KEY, timeout=60)
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = co.chat(
                model=settings.COHERE_CHAT_MODEL,
                message=EXTRACTION_PROMPT.format(text=chunk),
                preamble=(
                    "Eres un auditor médico experto en normativa colombiana (CIE10, CUPS, Ley 1438). "
                    "IMPORTANTE: Responde ÚNICAMENTE con el JSON solicitado, sin texto adicional ni bloques markdown."
                ),
                temperature=0,
            )
            text = response.text
            match = re.search(r'\{.*\}', text, re.DOTALL)
            raw = match.group() if match else text
            return json.loads(_try_fix_json_string(raw))
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"  ⚠️ Fragmento {idx} - JSON inválido de Cohere (intento {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(1)
        except Exception as e:
            last_error = e
            logger.warning(f"  ⚠️ Fragmento {idx} - Error Cohere (intento {attempt}/{max_retries}): {type(e).__name__}: {e}")
            if attempt < max_retries:
                time.sleep(2)

    # Fallback a OpenAI solo si Cohere falló todos los reintentos
    logger.warning(f"  🔄 Fragmento {idx} - Cohere falló {max_retries} veces, usando OpenAI como fallback")
    return {"_needs_openai_fallback": True, "chunk": chunk, "idx": idx}


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

        # Fragmentos de ~10,000 chars (~2,500 tokens) para respuesta rápida de Cohere
        max_chunk = 10000
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
            if settings.EXTRACTION_PROVIDER == "cohere":
                logger.info(f"🔵 Fragmento {idx}/{len(chunks)} → Cohere {settings.COHERE_CHAT_MODEL} (size {len(chunk)})")
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, _extract_with_cohere, chunk, idx)
                # Fallback a OpenAI si Cohere no pudo parsear JSON tras reintentos
                if result.get("_needs_openai_fallback"):
                    logger.info(f"  🔄 Fragmento {idx} → fallback OpenAI {settings.LLM_MODEL}")
                    try:
                        response = await client.chat.completions.create(
                            model=settings.LLM_MODEL,
                            messages=[
                                {"role": "system", "content": "Eres un auditor médico experto en normativa colombiana (CIE10, CUPS, Ley 1438)."},
                                {"role": "user", "content": EXTRACTION_PROMPT.format(text=result["chunk"])},
                            ],
                            temperature=0,
                            response_format={"type": "json_object"},
                        )
                        return json.loads(response.choices[0].message.content)
                    except Exception as e:
                        logger.error(f"  ❌ Fragmento {idx} - Fallback OpenAI también falló: {e}")
                        return {"error": f"Error en fragmento {idx}: {str(e)}"}
                return result

            logger.info(f"🔍 Fragmento {idx}/{len(chunks)} iniciando (size {len(chunk)})")
            max_retries = 4
            for attempt in range(max_retries):
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
                    return {"error": f"JSON malformado en fragmento {idx}: {str(e)}"}
                except Exception as e:
                    is_rate_limit = "429" in str(e) or "rate_limit" in str(e).lower() or "RateLimitError" in type(e).__name__
                    if is_rate_limit and attempt < max_retries - 1:
                        wait_secs = 15 * (attempt + 1)  # 15s, 30s, 45s
                        logger.warning(f"  ⏳ Fragmento {idx} - Rate limit (429). Esperando {wait_secs}s antes de reintentar (intento {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(wait_secs)
                        continue
                    logger.error(f"  ❌ Fragmento {idx} - Error OpenAI: {type(e).__name__}: {str(e)}")
                    if hasattr(e, 'response'):
                        logger.error(f"  📜 Respuesta HTTP: {getattr(e.response, 'status_code', 'N/A')}")
                    return {"error": f"Error en fragmento {idx}: {str(e)}"}
            return {"error": f"Fragmento {idx}: máximo de reintentos agotado"}

        # Ejecutar fragmentos en paralelo (OpenAI soporta alta concurrencia)
        logger.info(f"🔍 Procesando {len(chunks)} fragmento(s) en paralelo")
        results = list(await asyncio.gather(*[_call_chunk(c, i + 1) for i, c in enumerate(chunks)]))

        combined: dict = {}
        errors = []
        for r in results:
            if "error" in r:
                errors.append(r["error"])
            else:
                combined = _merge_clinical_dicts(combined, r)

        if errors:
            logger.warning(f"⚠️ {len(errors)} fragmento(s) fallaron: {errors}")
        if not combined:
            return {"error": "; ".join(errors)}

        logger.info(f"✅ Extracción completa, campos consolidados: {len(combined)}")
        if errors:
            logger.error(f"❌ Fragmentos fallidos: {json.dumps(errors, ensure_ascii=False, indent=2)}")
            combined["errores_fragmentos"] = errors
        logger.info(f"📊 Datos extraídos finales: {json.dumps(combined, ensure_ascii=False, indent=2)}")
        return combined

    except Exception as e:
        logger.error(f"❌ ERROR GLOBAL en extracción de variables: {type(e).__name__}: {str(e)}")
        if 'RateLimitError' in str(type(e)) or 'insufficient_quota' in str(e).lower():
            logger.error(f"💰 PROBLEMA DE CUOTA: La API key no tiene créditos suficientes")
            logger.error(f"💰 Solución: Recarga créditos en platform.openai.com/settings/billing")
        logger.exception("Traceback completo:")
        return {"error": str(e)}
