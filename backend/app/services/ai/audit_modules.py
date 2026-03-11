"""
Módulos de auditoría clínica basados en IA y reglas.
Normativa colombiana: Ley 1438/2011, Decreto 780/2016, Res. 1995/1999.
"""
from dataclasses import dataclass
from typing import List
from app.models.audit import AuditModule
from app.models.patient import RiskLevel

# Días de estancia esperados por código CIE10 (simplificado)
ESTANCIA_ESPERADA_CIE10 = {
    "J18": (5, 7),    # Neumonía
    "I21": (4, 7),    # IAM
    "K80": (3, 5),    # Colelitiasis
    "N39": (3, 5),    # ITU
    "J44": (5, 8),    # EPOC
}


@dataclass
class Finding:
    modulo: AuditModule
    descripcion: str
    riesgo: RiskLevel
    pagina: int | None
    recomendacion: str


def analyze_estancia(patient_data: dict) -> List[Finding]:
    """Módulo 1: Análisis de estancia hospitalaria."""
    findings = []
    dias_real = patient_data.get("dias_hospitalizacion")
    codigo = (patient_data.get("codigo_cie10") or "")[:3]

    if dias_real and codigo in ESTANCIA_ESPERADA_CIE10:
        min_d, max_d = ESTANCIA_ESPERADA_CIE10[codigo]
        if dias_real > max_d:
            exceso = dias_real - max_d
            findings.append(Finding(
                modulo=AuditModule.estancia,
                descripcion=f"Estancia prolongada: {dias_real} días vs {max_d} esperados para {codigo}. Exceso: {exceso} días.",
                riesgo=RiskLevel.alto if exceso > 3 else RiskLevel.medio,
                pagina=None,
                recomendacion="Verificar justificación clínica para la extensión de estancia. Documentar criterios de complejidad.",
            ))
    return findings


def analyze_cie10(patient_data: dict) -> List[Finding]:
    """Módulo 2: Verificación de coherencia diagnóstica CIE10."""
    findings = []
    codigo = patient_data.get("codigo_cie10")
    diagnostico = patient_data.get("diagnostico_principal", "")

    if not codigo:
        findings.append(Finding(
            modulo=AuditModule.cie10,
            descripcion="No se encontró código CIE10 asignado al diagnóstico principal.",
            riesgo=RiskLevel.alto,
            pagina=None,
            recomendacion="Asignar código CIE10 correspondiente. Glosa potencial por codificación incorrecta.",
        ))
    elif len(codigo) < 3:
        findings.append(Finding(
            modulo=AuditModule.cie10,
            descripcion=f"Código CIE10 incompleto: '{codigo}'. Requiere mínimo 3 caracteres.",
            riesgo=RiskLevel.medio,
            pagina=None,
            recomendacion="Completar la codificación CIE10 con especificidad adecuada.",
        ))
    return findings


def analyze_estudios(patient_data: dict) -> List[Finding]:
    """Módulo 3: Pertinencia de estudios paraclínicos."""
    findings = []
    estudios = patient_data.get("estudios_solicitados", [])

    for estudio in estudios:
        if isinstance(estudio, dict) and not estudio.get("resultado_disponible"):
            findings.append(Finding(
                modulo=AuditModule.estudios,
                descripcion=f"Estudio sin resultado reportado: {estudio.get('nombre', 'sin nombre')}.",
                riesgo=RiskLevel.medio,
                pagina=None,
                recomendacion="Verificar reporte del estudio en la historia clínica. Posible glosa por estudio sin soporte.",
            ))
    return findings


def analyze_glosas(patient_data: dict) -> List[Finding]:
    """Módulo 4: Detección de causas de glosa."""
    findings = []
    evoluciones = patient_data.get("evoluciones", [])
    medicamentos = patient_data.get("medicamentos", [])
    dias = patient_data.get("dias_hospitalizacion", 0) or 0

    # Verificar evoluciones diarias
    if dias > 0 and len(evoluciones) < dias:
        faltantes = dias - len(evoluciones)
        findings.append(Finding(
            modulo=AuditModule.glosas,
            descripcion=f"Evoluciones médicas insuficientes: {len(evoluciones)} registradas para {dias} días de hospitalización. Faltan {faltantes}.",
            riesgo=RiskLevel.alto,
            pagina=None,
            recomendacion="Completar evoluciones médicas diarias. Res. 1995/1999 exige registro diario obligatorio.",
        ))

    # Verificar medicamentos con indicación
    for med in medicamentos:
        if isinstance(med, dict) and not med.get("indicacion") and not med.get("frecuencia"):
            findings.append(Finding(
                modulo=AuditModule.glosas,
                descripcion=f"Medicamento sin indicación documentada: {med.get('nombre', 'sin nombre')}.",
                riesgo=RiskLevel.medio,
                pagina=None,
                recomendacion="Documentar indicación clínica del medicamento para evitar glosa.",
            ))

    return findings


def run_all_modules(patient_data: dict) -> List[Finding]:
    """Ejecuta todos los módulos de auditoría y retorna hallazgos consolidados."""
    findings = []
    findings.extend(analyze_estancia(patient_data))
    findings.extend(analyze_cie10(patient_data))
    findings.extend(analyze_estudios(patient_data))
    findings.extend(analyze_glosas(patient_data))
    return findings


def calculate_risk(findings: List[Finding]) -> RiskLevel:
    """Calcula el nivel de riesgo global basado en los hallazgos."""
    if any(f.riesgo == RiskLevel.alto for f in findings):
        return RiskLevel.alto
    if any(f.riesgo == RiskLevel.medio for f in findings):
        return RiskLevel.medio
    return RiskLevel.bajo
