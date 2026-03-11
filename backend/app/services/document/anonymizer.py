"""
Servicio de anonimización de datos personales en texto clínico.
Aplica expresiones regulares y NER básico para remover PII.
"""
import re

# Patrones colombianos de datos personales
PATTERNS = [
    # Cédula de ciudadanía
    (r'\b[Cc]\.?\s*[Cc]\.?\s*[Nn]?[oO°]?\.?\s*\d{6,12}\b', '[CC REDACTADA]'),
    # Nombre típico (2-4 palabras con mayúsculas)
    (r'\b(?:Paciente|Nombre|SR\.|SRA\.|DRA?\.|DR\.?)\.?\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3}', '[NOMBRE REDACTADO]'),
    # Teléfono colombiano
    (r'\b(?:\+57\s?)?(?:3\d{2}[\s-]?\d{3}[\s-]?\d{4}|[1-8]\d{6,7})\b', '[TELÉFONO REDACTADO]'),
    # Correo electrónico
    (r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b', '[CORREO REDACTADO]'),
    # Número de historia clínica
    (r'\b(?:HC|H\.C\.|Historia\s+[Cc]l[íi]nica)\s*[Nn]?[oO°]?\.?\s*\d{4,12}\b', '[HC REDACTADA]'),
    # Dirección (calle, carrera, avenida)
    (r'\b(?:Calle|Cra\.?|Carrera|Av\.?|Avenida|Diagonal|Transversal)\s+\d+[A-Z]?\s*[#\-]\s*\d+[A-Z]?\s*-\s*\d+', '[DIRECCIÓN REDACTADA]'),
]


def anonymize_text(text: str) -> str:
    """Remueve datos personales identificables del texto clínico."""
    result = text
    for pattern, replacement in PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def anonymize_pages(pages: list) -> list:
    """Anonimiza una lista de objetos PageContent."""
    for page in pages:
        page.text = anonymize_text(page.text)
    return pages
