"""
Servicio de extracción estructurada de variables clínicas usando LLM.
"""
import json
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

EXTRACTION_PROMPT = """Eres un experto en auditoría médica colombiana. Analiza la siguiente historia clínica
(ya anonimizada) y extrae las variables en formato JSON estricto.

Historia clínica:
{text}

Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:
{{
  "edad": null,
  "sexo": null,
  "cama": null,
  "diagnostico_principal": null,
  "codigo_cie10": null,
  "diagnosticos_secundarios": [],
  "fecha_ingreso": null,
  "dias_hospitalizacion": null,
  "dias_esperados": null,
  "medicamentos": [
    {{"nombre": "", "dosis": "", "frecuencia": ""}}
  ],
  "antecedentes": {{
    "patologicos": [],
    "quirurgicos": [],
    "familiares": []
  }},
  "estudios_solicitados": [
    {{"nombre": "", "fecha": "", "resultado_disponible": false}}
  ],
  "procedimientos": [],
  "evoluciones": [
    {{"fecha": "", "resumen": ""}}
  ]
}}

Usa null para valores no encontrados. Solo devuelve JSON, sin texto adicional."""


async def extract_clinical_variables(text: str) -> dict:
    """Extrae variables clínicas estructuradas del texto de la historia clínica."""
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": "Eres un auditor médico experto en normativa colombiana (CIE10, CUPS, Ley 1438)."},
                {"role": "user", "content": EXTRACTION_PROMPT.format(text=text[:12000])},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}
