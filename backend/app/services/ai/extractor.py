"""
Servicio de extracción estructurada de variables clínicas usando LLM.
"""
import json
import logging
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

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
- dias_hospitalizacion: Calcular diferencia entre fecha_ingreso y fecha actual/egreso
- dias_esperados: Buscar en el texto si mencionan tiempo esperado de hospitalización
- antecedentes.farmacologicos: Medicación previa o alergias conocidas
- Usa null para valores no encontrados, [] para arrays vacíos
- Solo devuelve JSON, sin texto adicional"""


async def _merge_clinical_dicts(base: dict, other: dict) -> dict:
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


async def extract_clinical_variables(text: str) -> dict:
    """Extrae variables clínicas estructuradas del texto de la historia clínica.

    Maneja textos largos dividiéndolos en fragmentos para evitar cortar información
    importante en el prompt del modelo. Combina los resultados parciales en un
    único diccionario con lógica de fusión razonable.
    """
    try:
        logger.info(f"🔍 Extrayendo variables clínicas (texto: {len(text)} chars)...")
        logger.info(f"🔑 API Key configurada: {settings.OPENAI_API_KEY[:20]}...")
        logger.info(f"🤖 Modelo: {settings.LLM_MODEL}")

        # dividir en pedazos de aproximadamente N chars
        max_chunk = 8000
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_chunk, len(text))
            # intentar romper en salto de línea para no cortar frases
            if end < len(text):
                nl = text.rfind("\n", start, end)
                if nl > start:
                    end = nl
            chunks.append(text[start:end])
            start = end
        logger.info(f"🔍 Texto dividido en {len(chunks)} fragmento(s) para extracción")

        combined: dict = {}
        for idx, chunk in enumerate(chunks, start=1):
            logger.info(f"🔍 Procesando fragmento {idx}/{len(chunks)} (size {len(chunk)})")
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
            logger.info(f"  ✅ Resultado fragmento {idx}: {json.dumps(result, ensure_ascii=False)}")
            combined = _merge_clinical_dicts(combined, result)

        logger.info(f"✅ Extracción completa, campos consolidados: {len(combined)}")
        logger.info(f"📊 Datos extraídos finales: {json.dumps(combined, ensure_ascii=False, indent=2)}")
        return combined

    except Exception as e:
        logger.error(f"❌ ERROR en extracción de variables: {type(e).__name__}: {str(e)}")
        logger.exception("Traceback completo:")
        return {"error": str(e)}
