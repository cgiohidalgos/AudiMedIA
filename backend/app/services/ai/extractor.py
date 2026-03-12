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


async def extract_clinical_variables(text: str) -> dict:
    """Extrae variables clínicas estructuradas del texto de la historia clínica."""
    try:
        logger.info(f"🔍 Extrayendo variables clínicas (texto: {len(text)} chars)...")
        logger.info(f"🔑 API Key configurada: {settings.OPENAI_API_KEY[:20]}...")
        logger.info(f"🤖 Modelo: {settings.LLM_MODEL}")
        
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": "Eres un auditor médico experto en normativa colombiana (CIE10, CUPS, Ley 1438)."},
                {"role": "user", "content": EXTRACTION_PROMPT.format(text=text[:12000])},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        
        result = json.loads(response.choices[0].message.content)
        logger.info(f"✅ Extracción exitosa: {len(result)} campos encontrados")
        logger.info(f"📊 Datos extraídos: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ ERROR en extracción de variables: {type(e).__name__}: {str(e)}")
        logger.exception("Traceback completo:")
        return {"error": str(e)}
