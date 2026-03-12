"""
Módulos de auditoría clínica basados en IA y reglas clínicas.

Normativa colombiana aplicada:
- Ley 1438/2011: Sistema de salud y auditoría concurrente
- Decreto 780/2016: Sector Salud y Protección Social
- Resolución 1995/1999: Historia clínica y registros obligatorios
- Resolución 3100/2019: Procedimientos y tarifas

Este módulo implementa 4 motores de auditoría:
1. Análisis de Estancia Hospitalaria
2. Verificación de Pertinencia CIE-10
3. Auditoría de Estudios y Procedimientos
4. Detección de Causales de Glosa
"""
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from datetime import datetime, date
from pathlib import Path

from app.models.audit import AuditModule
from app.models.patient import RiskLevel

# Rutas a las tablas de referencia
BASE_DIR = Path(__file__).parent.parent.parent / "data"
CIE10_ESTANCIA_PATH = BASE_DIR / "cie10_estancia.json"
CIE10_DEFINICIONES_PATH = BASE_DIR / "cie10_definiciones.json"
PROCEDIMIENTOS_CUPS_PATH = BASE_DIR / "procedimientos_cups.json"

# Cache global para las tablas de referencia (se cargan una sola vez)
_ESTANCIA_CACHE: Optional[Dict] = None
_DEFINICIONES_CACHE: Optional[Dict] = None
_PROCEDIMIENTOS_CACHE: Optional[Dict] = None


@dataclass
class Finding:
    """Hallazgo de auditoría con toda la información necesaria."""
    modulo: AuditModule
    descripcion: str
    riesgo: RiskLevel
    pagina: Optional[int]
    recomendacion: str
    valor_glosa_estimado: Optional[float] = None  # Valor en COP
    normativa_aplicable: Optional[str] = None
    categoria: Optional[str] = None


# ============================================================================
# FUNCIONES DE CARGA DE DATOS
# ============================================================================

def load_estancia_data() -> Dict:
    """Carga tabla de días esperados de estancia por CIE-10."""
    global _ESTANCIA_CACHE
    if _ESTANCIA_CACHE is None:
        try:
            with open(CIE10_ESTANCIA_PATH, 'r', encoding='utf-8') as f:
                _ESTANCIA_CACHE = json.load(f)
        except FileNotFoundError:
            _ESTANCIA_CACHE = {"codigos": {}}
    return _ESTANCIA_CACHE


def load_definiciones_data() -> Dict:
    """Carga definiciones clínicas de CIE-10."""
    global _DEFINICIONES_CACHE
    if _DEFINICIONES_CACHE is None:
        try:
            with open(CIE10_DEFINICIONES_PATH, 'r', encoding='utf-8') as f:
                _DEFINICIONES_CACHE = json.load(f)
        except FileNotFoundError:
            _DEFINICIONES_CACHE = {"definiciones": {}}
    return _DEFINICIONES_CACHE


def load_procedimientos_data() -> Dict:
    """Carga tabla de procedimientos CUPS."""
    global _PROCEDIMIENTOS_CACHE
    if _PROCEDIMIENTOS_CACHE is None:
        try:
            with open(PROCEDIMIENTOS_CUPS_PATH, 'r', encoding='utf-8') as f:
                _PROCEDIMIENTOS_CACHE = json.load(f)
        except FileNotFoundError:
            _PROCEDIMIENTOS_CACHE = {
                "estudios_imagenologicos": {},
                "laboratorio_clinico": {},
                "procedimientos_quirurgicos": {},
                "glosas_frecuentes": {}
            }
    return _PROCEDIMIENTOS_CACHE


def get_codigo_cie10_base(codigo: str) -> str:
    """
    Extra el código base CIE-10 (3 primeros caracteres sin subcódigo).
    Ejemplos: I21.0 → I21, J18.9 → J18, K35.2 → K35
    """
    if not codigo:
        return ""
    # Remover espacios y convertir a mayúsculas
    codigo = codigo.strip().upper()
    # Tomar siempre la parte antes del punto (si existe) como base
    base = codigo.split(".", 1)[0]
    # Retornar solo los primeros 3 caracteres de la base (categoría CIE-10)
    return base[:3] if len(base) > 3 else base


# ============================================================================
# MÓDULO 1: ANÁLISIS DE ESTANCIA HOSPITALARIA
# ============================================================================

def analyze_estancia(patient_data: dict) -> List[Finding]:
    """
    Módulo 1: Análisis de estancia hospitalaria.
    
    Evalúa:
    - Días reales vs días esperados según CIE-10
    - Justificación de estancia prolongada
    - Necesidad de UCI vs hospitalización general
    - Costo estimado por días excedentes
    
    Args:
        patient_data: Diccionario con datos del paciente
            - dias_hospitalizacion: int
            - fecha_ingreso: str (YYYY-MM-DD)
            - codigo_cie10: str
            - diagnostico_principal: str
            - en_uci: bool
            - evoluciones: List[dict]
    
    Returns:
        Lista de hallazgos (Finding)
    """
    findings = []
    estancia_db = load_estancia_data()
    codigos = estancia_db.get("codigos", {})
    
    dias_real = patient_data.get("dias_hospitalizacion")
    codigo_completo = patient_data.get("codigo_cie10", "")
    diagnostico = patient_data.get("diagnostico_principal", "Sin diagnóstico")
    en_uci = patient_data.get("en_uci", False)
    evoluciones = patient_data.get("evoluciones", [])
    
    if not dias_real or dias_real <= 0:
        return findings  # No hay suficiente información
    
    # Buscar código en tabla (primero completo, luego base)
    codigo_info = None
    if codigo_completo in codigos:
        codigo_info = codigos[codigo_completo]
        codigo_usado = codigo_completo
    else:
        # Intentar con código base (primeros 3 caracteres)
        codigo_base = get_codigo_cie10_base(codigo_completo)
        if codigo_base in codigos:
            codigo_info = codigos[codigo_base]
            codigo_usado = codigo_base
    
    if not codigo_info:
        # CIE-10 no está en nuestra tabla de referencia
        if dias_real > 10:  # Alerta genérica para estancias muy largas
            findings.append(Finding(
                modulo=AuditModule.estancia,
                descripcion=f"Estancia de {dias_real} días sin referencia en tabla CIE-10 (código: {codigo_completo}). Requiere revisión manual.",
                riesgo=RiskLevel.medio,
                pagina=None,
                recomendacion="Verificar pertinencia de hospitalización prolongada y documentar justificación clínica.",
                normativa_aplicable="Guías clínicas institucionales",
                categoria="estancia_sin_referencia"
            ))
        return findings
    
    # Extraer días esperados
    dias_min = codigo_info.get("dias_min", 0)
    dias_max = codigo_info.get("dias_max", 0)
    nombre_diagnostico = codigo_info.get("nombre", diagnostico)
    requiere_uci = codigo_info.get("requiere_uci", False)
    
    # Proteger contra valores inválidos de dias_max (0 o negativos)
    if not dias_max or dias_max <= 0:
        # Sin referencia válida de días esperados
        if dias_real > 10:
            findings.append(Finding(
                modulo=AuditModule.estancia,
                descripcion=f"Estancia de {dias_real} días con referencia CIE-10 inválida (días_max={dias_max}). Requiere revisión manual.",
                riesgo=RiskLevel.medio,
                pagina=None,
                recomendacion="Verificar pertinencia de hospitalización prolongada y documentar justificación clínica.",
                normativa_aplicable="Guías clínicas institucionales",
                categoria="estancia_sin_referencia_valida"
            ))
        return findings
    
    # 1. Verificar estancia prolongada
    if dias_real > dias_max:
        exceso = dias_real - dias_max
        porcentaje_exceso = (exceso / dias_max) * 100
        
        # Estimar costo por días excedentes (tarifa promedio $800,000/día)
        costo_exceso = exceso * 800000
        
        # Determinar nivel de riesgo
        if exceso > 5:
            riesgo = RiskLevel.alto
        elif exceso > 2:
            riesgo = RiskLevel.medio
        else:
            riesgo = RiskLevel.bajo
        
        # Verificar si hay justificación en evoluciones
        # Soportar diferentes nombres de campo: texto, resumen, nota
        tiene_justificacion = any(
            (
                lambda texto_ev: (
                    "prolongad" in texto_ev
                    or "complicac" in texto_ev
                    or "complejidad" in texto_ev
                )
            )(
                " ".join(
                    str(ev.get(campo, "")) for campo in ("texto", "resumen", "nota")
                ).lower()
            )
            for ev in evoluciones
        )
        
        recomendacion_texto = (
            f"Documentar criterios de complejidad que justifiquen {exceso} días adicionales. "
            f"Considerar evaluación para egreso o paso a menor nivel de atención."
        )
        
        if not tiene_justificacion:
            recomendacion_texto += " ⚠️ No se encontró justificación explícita en evoluciones."
        
        findings.append(Finding(
            modulo=AuditModule.estancia,
            descripcion=(
                f"Estancia prolongada: {dias_real} días vs {dias_min}-{dias_max} días esperados "
                f"para {nombre_diagnostico} (CIE-10: {codigo_usado}). "
                f"Exceso: {exceso} días ({porcentaje_exceso:.0f}%)."
            ),
            riesgo=riesgo,
            pagina=None,
            recomendacion=recomendacion_texto,
            valor_glosa_estimado=costo_exceso,
            normativa_aplicable="Guías clínicas - Tarifario SOAT",
            categoria="estancia_prolongada"
        ))
    
    # 2. Verificar necesidad de UCI
    if requiere_uci and not en_uci:
        findings.append(Finding(
            modulo=AuditModule.estancia,
            descripcion=(
                f"Diagnóstico {nombre_diagnostico} (CIE-10: {codigo_usado}) "
                f"generalmente requiere manejo en UCI según guías clínicas."
            ),
            riesgo=RiskLevel.medio,
            pagina=None,
            recomendacion=(
                "Evaluar criterios para ingreso a UCI. "
                "Si el paciente está estable, documentar justificación de manejo en piso."
            ),
            normativa_aplicable="Protocolo institucional de UCI",
            categoria="ubicacion_inadecuada"
        ))
    elif not requiere_uci and en_uci and dias_real > 3:
        # Paciente en UCI sin necesidad evidente
        findings.append(Finding(
            modulo=AuditModule.estancia,
            descripcion=(
                f"Paciente con {nombre_diagnostico} (CIE-10: {codigo_usado}) lleva {dias_real} días en UCI. "
                f"Este diagnóstico no requiere UCI habitualmente."
            ),
            riesgo=RiskLevel.medio,
            pagina=None,
            recomendacion=(
                "Evaluar criterios para traslado a hospitalización general. "
                "Documentar indicación de UCI si hay factores de complejidad adicionales."
            ),
            valor_glosa_estimado=(dias_real - 2) * 1200000,  # Diferencia tarifa UCI vs piso
            normativa_aplicable="Protocolo institucional de UCI",
            categoria="uci_innecesaria"
        ))
    
    # 3. Verificar estancia muy corta (alerta informativa)
    if dias_real < dias_min:
        findings.append(Finding(
            modulo=AuditModule.estancia,
            descripcion=(
                f"Estancia de {dias_real} días menor a lo esperado ({dias_min}-{dias_max} días) "
                f"para {nombre_diagnostico}. Verificar resolución completa del cuadro."
            ),
            riesgo=RiskLevel.bajo,
            pagina=None,
            recomendacion="Confirmar que se cumplieron criterios de egreso y seguimiento ambulatorio.",
            normativa_aplicable="Guías clínicas",
            categoria="estancia_corta"
        ))
    
    return findings



# ============================================================================
# MÓDULO 2: PERTINENCIA CIE-10
# ============================================================================

def analyze_cie10(patient_data: dict) -> List[Finding]:
    """
    Módulo 2: Pertinencia de código CIE-10.
    
    Evalúa:
    - Completitud del código (4to dígito presente)
    - Coherencia entre síntomas documentados y criterios diagnósticos
    - Presencia de exámenes requeridos
    - Sugerencia de códigos alternativos si aplica
    
    Args:
        patient_data: Diccionario con datos del paciente
            - codigo_cie10: str
            - diagnostico_principal: str
            - sintomas: List[str] o str
            - examenes_realizados: List[str]
            - antecedentes: str
    
    Returns:
        Lista de hallazgos (Finding)
    """
    findings = []
    definiciones_db = load_definiciones_data()
    definiciones = definiciones_db.get("definiciones", {})
    
    codigo = patient_data.get("codigo_cie10", "")
    diagnostico = patient_data.get("diagnostico_principal", "")
    sintomas_raw = patient_data.get("sintomas", [])
    examenes = patient_data.get("examenes_realizados", [])
    antecedentes = patient_data.get("antecedentes", "")
    
    # Normalizar síntomas a lista
    if isinstance(sintomas_raw, str):
        sintomas = [s.strip().lower() for s in sintomas_raw.split(",") if s.strip()]
    else:
        sintomas = [str(s).lower() for s in sintomas_raw]
    
    # 1. Verificar completitud del código
    if not codigo or len(codigo) < 3:
        findings.append(Finding(
            modulo=AuditModule.cie10,
            descripcion="Código CIE-10 ausente o incompleto.",
            riesgo=RiskLevel.alto,
            pagina=None,
            recomendacion="Asignar código CIE-10 completo con 4to dígito según guía OMS.",
            valor_glosa_estimado=300000,  # Glosa por codificación inadecuada
            normativa_aplicable="Resolución 3374 de 2000 - CIE-10",
            categoria="codigo_ausente"
        ))
        return findings
    
    if "." not in codigo or len(codigo.split(".")[1]) == 0:
        findings.append(Finding(
            modulo=AuditModule.cie10,
            descripcion=f"Código CIE-10 sin 4to dígito: {codigo}. Falta especificidad clínica.",
            riesgo=RiskLevel.medio,
            pagina=None,
            recomendacion=f"Completar código con 4to dígito basado en características clínicas de {diagnostico}.",
            valor_glosa_estimado=200000,
            normativa_aplicable="Resolución 3374 de 2000 - CIE-10",
            categoria="codigo_incompleto"
        ))
    
    # 2. Buscar definición clínica
    codigo_base = get_codigo_cie10_base(codigo)
    definicion = None
    codigo_validar = None
    
    # Intentar match exacto primero
    if codigo in definiciones:
        definicion = definiciones[codigo]
        codigo_validar = codigo
    elif codigo_base in definiciones:
        definicion = definiciones[codigo_base]
        codigo_validar = codigo_base
    
    if not definicion:
        # No hay definición en nuestra base, solo alerta informativa
        if len(sintomas) == 0:
            findings.append(Finding(
                modulo=AuditModule.cie10,
                descripcion=f"No se documentaron síntomas para validar coherencia del diagnóstico {diagnostico} (CIE-10: {codigo}).",
                riesgo=RiskLevel.bajo,
                pagina=None,
                recomendacion="Registrar anamnesis completa con síntomas principales para futuras auditorías.",
                normativa_aplicable="Resolución 1995 de 1999 - Historia Clínica",
                categoria="sintomas_no_documentados"
            ))
        return findings
    
    # 3. Validar criterios diagnósticos
    criterios_mayores = definicion.get("criterios_mayores", [])
    sintomas_frecuentes = definicion.get("sintomas_frecuentes", [])
    examenes_requeridos = definicion.get("examenes_requeridos", [])
    codigos_alternativos = definicion.get("codigos_alternativos", [])
    
    # Matching de síntomas con criterios (fuzzy simple)
    criterios_encontrados = []
    for criterio in criterios_mayores:
        for sintoma in sintomas:
            # Match simple por substring
            if criterio.lower() in sintoma or sintoma in criterio.lower():
                criterios_encontrados.append(criterio)
                break
    
    sintomas_coincidentes = []
    for sintoma_frecuente in sintomas_frecuentes:
        for sintoma in sintomas:
            if sintoma_frecuente.lower() in sintoma or sintoma in sintoma_frecuente.lower():
                sintomas_coincidentes.append(sintoma_frecuente)
                break
    
    # 4. Determinar pertinencia
    total_criterios = len(criterios_mayores)
    criterios_cumplidos = len(criterios_encontrados)
    
    if total_criterios > 0:
        porcentaje_criterios = (criterios_cumplidos / total_criterios) * 100
        
        if criterios_cumplidos == 0:
            # Ningún criterio mayor documentado
            findings.append(Finding(
                modulo=AuditModule.cie10,
                descripcion=(
                    f"Diagnóstico {diagnostico} (CIE-10: {codigo_validar}) sin criterios mayores documentados. "
                    f"Se esperan: {', '.join(criterios_mayores)}."
                ),
                riesgo=RiskLevel.alto,
                pagina=None,
                recomendacion=(
                    f"Revisar historia clínica y documentar hallazgos que respalden el diagnóstico. "
                    f"Si no cumple criterios, considerar códigos alternativos: {', '.join(codigos_alternativos) if codigos_alternativos else 'N/A'}."
                ),
                valor_glosa_estimado=500000,  # Alto riesgo de glosa por dx inadecuado
                normativa_aplicable="Guías clínicas basadas en evidencia",
                categoria="criterios_no_cumplidos"
            ))
        elif porcentaje_criterios < 50:
            # Solo algunos criterios cumplidos
            criterios_faltantes = [c for c in criterios_mayores if c not in criterios_encontrados]
            findings.append(Finding(
                modulo=AuditModule.cie10,
                descripcion=(
                    f"Diagnóstico {diagnostico} (CIE-10: {codigo_validar}) con criterios incompletos. "
                    f"Cumple {criterios_cumplidos}/{total_criterios} criterios mayores."
                ),
                riesgo=RiskLevel.medio,
                pagina=None,
                recomendacion=(
                    f"Verificar y documentar: {', '.join(criterios_faltantes)}. "
                    f"Si persiste inconsistencia, considerar: {', '.join(codigos_alternativos) if codigos_alternativos else 'revisión manual'}."
                ),
                valor_glosa_estimado=300000,
                normativa_aplicable="Guías clínicas basadas en evidencia",
                categoria="criterios_parcialmente_cumplidos"
            ))
    
    # 5. Verificar exámenes requeridos
    examenes_faltantes = []
    if examenes_requeridos:
        for examen_requerido in examenes_requeridos:
            encontrado = any(
                examen_requerido.lower() in str(examen).lower() 
                for examen in examenes
            )
            if not encontrado:
                examenes_faltantes.append(examen_requerido)
        
        if examenes_faltantes:
            findings.append(Finding(
                modulo=AuditModule.cie10,
                descripcion=(
                    f"Faltan exámenes diagnósticos para {diagnostico} (CIE-10: {codigo_validar}): "
                    f"{', '.join(examenes_faltantes)}."
                ),
                riesgo=RiskLevel.medio,
                pagina=None,
                recomendacion=(
                    f"Solicitar y documentar resultado de: {', '.join(examenes_faltantes)}. "
                    f"Estos son esenciales para confirmar el diagnóstico según guías clínicas."
                ),
                valor_glosa_estimado=200000,
                normativa_aplicable="Guías clínicas institucionales",
                categoria="examenes_faltantes"
            ))
    
    # 6. Hallazgo positivo si todo está OK
    if total_criterios > 0 and criterios_cumplidos >= total_criterios * 0.7 and len(examenes_faltantes) == 0:
        findings.append(Finding(
            modulo=AuditModule.cie10,
            descripcion=(
                f"Diagnóstico {diagnostico} (CIE-10: {codigo_validar}) adecuadamente documentado. "
                f"Cumple {criterios_cumplidos}/{total_criterios} criterios mayores."
            ),
            riesgo=RiskLevel.bajo,
            pagina=None,
            recomendacion="Mantener calidad de documentación clínica.",
            normativa_aplicable="Guías clínicas basadas en evidencia",
            categoria="diagnostico_adecuado"
        ))
    
    return findings



# ============================================================================
# MÓDULO 3: PERTINENCIA DE ESTUDIOS Y PROCEDIMIENTOS
# ============================================================================

def analyze_estudios(patient_data: dict) -> List[Finding]:
    """
    Módulo 3: Pertinencia de estudios y procedimientos.
    
    Evalúa:
    - Estudios solicitados sin resultados dentro del tiempo esperado
    - Indicación clínica documentada para cada procedimiento
    - Coherencia entre diagnóstico y estudios solicitados
    - Presencia de consentimiento informado para procedimientos críticos
    
    Args:
        patient_data: Diccionario con datos del paciente
            - estudios_solicitados: List[dict] con campos: nombre, codigo_cups, fecha_solicitud, resultado_disponible, resultado_fecha
            - procedimientos_realizados: List[dict] con campos: nombre, codigo_cups, consentimiento_firmado, indicacion
            - codigo_cie10: str
            - diagnostico_principal: str
            - dias_hospitalizacion: int
    
    Returns:
        Lista de hallazgos (Finding)
    """
    findings = []
    procedimientos_db = load_procedimientos_data()
    
    estudios_ref = procedimientos_db.get("estudios_imagenologicos", {})
    laboratorio_ref = procedimientos_db.get("laboratorio_clinico", {})
    procedimientos_ref = procedimientos_db.get("procedimientos_quirurgicos", {})
    
    estudios = patient_data.get("estudios_solicitados", [])
    # Aceptar tanto "procedimientos_realizados" (documentado) como "procedimientos"
    # (nombre usado por el extractor/pipeline), priorizando el más específico.
    procedimientos = patient_data.get("procedimientos_realizados") or patient_data.get("procedimientos", [])
    codigo_cie10 = patient_data.get("codigo_cie10", "")
    diagnostico = patient_data.get("diagnostico_principal", "")
    dias_hospitalizacion = patient_data.get("dias_hospitalizacion", 0)
    
    # 1. Verificar estudios imagenológicos sin resultados
    for estudio in estudios:
        if not isinstance(estudio, dict):
            continue
        
        nombre = estudio.get("nombre", "").lower()
        resultado_disponible = estudio.get("resultado_disponible", False)
        # Soportar tanto 'fecha_solicitud' (nombre esperado) como 'fecha' (nombre usado por el extractor)
        fecha_solicitud = estudio.get("fecha_solicitud") or estudio.get("fecha")  # Formato: YYYY-MM-DD o datetime
        codigo_cups = estudio.get("codigo_cups")
        
        if not resultado_disponible:
            # Buscar en estudios_ref para ver tiempo esperado
            estudio_info = None
            # Primero, intentar por código CUPS si está disponible
            if codigo_cups:
                estudio_info = estudios_ref.get(codigo_cups) or laboratorio_ref.get(codigo_cups)
            
            # Si no se encontró por código, intentar matchear por nombre del estudio
            if not estudio_info:
                for info in estudios_ref.values():
                    ref_nombre = str(info.get("nombre", "")).lower()
                    if ref_nombre and (ref_nombre in nombre or nombre in ref_nombre):
                        estudio_info = info
                        break
            
            if not estudio_info:
                # Buscar en laboratorio por nombre
                for info in laboratorio_ref.values():
                    ref_nombre = str(info.get("nombre", "")).lower()
                    if ref_nombre and (ref_nombre in nombre or nombre in ref_nombre):
                        estudio_info = info
                        break
            
            tiempo_esperado = None
            if estudio_info:
                tiempo_esperado = estudio_info.get("tiempo_resultado", "24 horas")
            
            # Calcular días desde solicitud (si hay fecha)
            dias_desde_solicitud = None
            if fecha_solicitud:
                try:
                    if isinstance(fecha_solicitud, str):
                        from datetime import datetime
                        fecha_sol_dt = datetime.fromisoformat(fecha_solicitud.replace("Z", "+00:00"))
                        hoy = datetime.now()
                        dias_desde_solicitud = (hoy - fecha_sol_dt).days
                except Exception:
                    pass
            
            # Determinar riesgo
            if dias_desde_solicitud is not None:
                if dias_desde_solicitud > 5:
                    riesgo = RiskLevel.alto
                elif dias_desde_solicitud > 2:
                    riesgo = RiskLevel.medio
                else:
                    riesgo = RiskLevel.bajo
            else:
                riesgo = RiskLevel.medio
            
            findings.append(Finding(
                modulo=AuditModule.estudios,
                descripcion=(
                    f"Estudio '{estudio.get('nombre', 'sin nombre')}' sin resultado reportado. "
                    f"{'Tiempo desde solicitud: ' + str(dias_desde_solicitud) + ' días.' if dias_desde_solicitud else 'Fecha de solicitud no disponible.'} "
                    f"{'Tiempo esperado: ' + tiempo_esperado + '.' if tiempo_esperado else ''}"
                ),
                riesgo=riesgo,
                pagina=None,
                recomendacion=(
                    "Gestionar resultado con laboratorio/imagenología. "
                    "Si el estudio no se realizó dentro del tiempo establecido, documentar razón. "
                    "Posible glosa por estudio sin reporte."
                ),
                valor_glosa_estimado=150000,  # Valor promedio estudio sin resultado
                normativa_aplicable="Resolución 1995 de 1999 - Historia Clínica",
                categoria="estudio_sin_resultado"
            ))
    
    # 2. Verificar indicación clínica para estudios
    for estudio in estudios:
        if not isinstance(estudio, dict):
            continue
        
        nombre = estudio.get("nombre", "").lower()
        indicacion = estudio.get("indicacion", "")
        
        if not indicacion or len(indicacion.strip()) < 10:
            # Buscar si el estudio requiere justificación especial
            estudio_info = None
            for key, info in estudios_ref.items():
                if key.lower() in nombre or nombre in key.lower():
                    estudio_info = info
                    break
            
            requiere_justificacion = False
            if estudio_info:
                requiere_justificacion = estudio_info.get("requiere_justificacion", False)
            
            if requiere_justificacion:
                findings.append(Finding(
                    modulo=AuditModule.estudios,
                    descripcion=f"Estudio '{estudio.get('nombre')}' sin indicación clínica documentada. Este estudio requiere justificación médica explícita.",
                    riesgo=RiskLevel.medio,
                    pagina=None,
                    recomendacion="Documentar indicación clínica clara que justifique la necesidad del estudio según el diagnóstico.",
                    valor_glosa_estimado=200000,
                    normativa_aplicable="Acuerdo 256 de 2001 - CUPS",
                    categoria="estudio_sin_indicacion"
                ))
    
    # 3. Verificar consentimiento informado para procedimientos
    for procedimiento in procedimientos:
        if not isinstance(procedimiento, dict):
            continue
        
        nombre = procedimiento.get("nombre", "").lower()
        consentimiento = procedimiento.get("consentimiento_firmado", False)
        indicacion = procedimiento.get("indicacion", "")
        
        # Buscar en procedimientos quirúrgicos
        proc_info = None
        for key, info in procedimientos_ref.items():
            if key.lower() in nombre or nombre in key.lower():
                proc_info = info
                break
        
        if proc_info:
            requiere_consentimiento = proc_info.get("requiere_consentimiento", True)
            
            if requiere_consentimiento and not consentimiento:
                findings.append(Finding(
                    modulo=AuditModule.estudios,
                    descripcion=f"Procedimiento '{procedimiento.get('nombre')}' realizado sin consentimiento informado documentado.",
                    riesgo=RiskLevel.alto,
                    pagina=None,
                    recomendacion=(
                        "Documentar consentimiento informado firmado por el paciente o familiar. "
                        "Este es un requisito legal para procedimientos invasivos (Ley 23 de 1981)."
                    ),
                    valor_glosa_estimado=500000,  # Glosa alta por tema legal
                    normativa_aplicable="Ley 23 de 1981 - Ética Médica / Res. 1995/1999",
                    categoria="consentimiento_faltante"
                ))
            
            if not indicacion or len(indicacion.strip()) < 10:
                findings.append(Finding(
                    modulo=AuditModule.estudios,
                    descripcion=f"Procedimiento '{procedimiento.get('nombre')}' sin indicación médica documentada en historia clínica.",
                    riesgo=RiskLevel.medio,
                    pagina=None,
                    recomendacion="Documentar claramente la indicación médica que justifica el procedimiento.",
                    valor_glosa_estimado=250000,
                    normativa_aplicable="Resolución 1995 de 1999",
                    categoria="procedimiento_sin_indicacion"
                ))
    
    return findings



# ============================================================================
# MÓDULO 4: DETECCIÓN DE CAUSAS DE GLOSA
# ============================================================================

def analyze_glosas(patient_data: dict) -> List[Finding]:
    """
    Módulo 4: Detección de causas frecuentes de glosa.
    
    Evalúa:
    - Evoluciones médicas diarias faltantes
    - Medicamentos sin orden médica o indicación
    - Procedimientos sin consentimiento informado
    - Estudios sin resultados documentados
    - Estancias prolongadas sin justificación clínica
    
    Args:
        patient_data: Diccionario con datos del paciente
            - evoluciones: List[dict] con fecha de cada evolución
            - medicamentos: List[dict] con nombre, orden_medica, indicacion
            - dias_hospitalizacion: int
            - fecha_ingreso: str
            - estudios_solicitados: List
            - procedimientos_realizados: List
            - codigo_cie10: str
    
    Returns:
        Lista de hallazgos (Finding) con valor_glosa_estimado
    """
    findings = []
    procedimientos_db = load_procedimientos_data()
    glosas_ref = procedimientos_db.get("glosas_frecuentes", {})
    
    evoluciones = patient_data.get("evoluciones", [])
    medicamentos = patient_data.get("medicamentos", [])
    dias_hospitalizacion = patient_data.get("dias_hospitalizacion", 0) or 0
    estudios = patient_data.get("estudios_solicitados", [])
    # Aceptar tanto "procedimientos_realizados" como "procedimientos"
    procedimientos = patient_data.get("procedimientos_realizados") or patient_data.get("procedimientos", [])
    
    # 1. Verificar evoluciones médicas diarias (Res. 1995/1999)
    if dias_hospitalizacion > 0:
        evoluciones_registradas = len(evoluciones)
        if evoluciones_registradas < dias_hospitalizacion:
            evoluciones_faltantes = dias_hospitalizacion - evoluciones_registradas
            
            # Obtener valor de glosa para evolución diaria
            glosa_evolucion = glosas_ref.get("evolucion_diaria", {})
            valor_glosa_unitario = glosa_evolucion.get("valor_promedio_glosa", 150000)
            valor_total_glosa = evoluciones_faltantes * valor_glosa_unitario
            
            findings.append(Finding(
                modulo=AuditModule.glosas,
                descripcion=(
                    f"Evoluciones médicas insuficientes: {evoluciones_registradas} registradas "
                    f"para {dias_hospitalizacion} días de hospitalización. "
                    f"Faltan {evoluciones_faltantes} evoluciones."
                ),
                riesgo=RiskLevel.alto,
                pagina=None,
                recomendacion=(
                    "Completar evoluciones médicas diarias. La Resolución 1995/1999 exige "
                    "registro diario obligatorio del estado del paciente, plan diagnóstico y terapéutico."
                ),
                valor_glosa_estimado=valor_total_glosa,
                normativa_aplicable="Resolución 1995 de 1999 - Art. 3, Numeral 16",
                categoria="evolucion_diaria_faltante"
            ))
        
        # Verificar evoluciones con fechas específicas (si están disponibles)
        if evoluciones and all(isinstance(ev, dict) and "fecha" in ev for ev in evoluciones):
            from datetime import datetime, timedelta
            
            try:
                fecha_ingreso_str = patient_data.get("fecha_ingreso")
                if fecha_ingreso_str:
                    fecha_ingreso = datetime.fromisoformat(fecha_ingreso_str.replace("Z", "+00:00"))
                    
                    # Crear set de fechas de evoluciones
                    fechas_evoluciones = set()
                    for ev in evoluciones:
                        fecha_ev_str = ev.get("fecha", "")
                        if fecha_ev_str:
                            fecha_ev = datetime.fromisoformat(fecha_ev_str.replace("Z", "+00:00"))
                            fechas_evoluciones.add(fecha_ev.date())
                    
                    # Verificar cada día de hospitalización
                    dias_sin_evolucion = []
                    for dia in range(dias_hospitalizacion):
                        fecha_revisar = (fecha_ingreso + timedelta(days=dia)).date()
                        if fecha_revisar not in fechas_evoluciones:
                            dias_sin_evolucion.append(fecha_revisar.strftime("%Y-%m-%d"))
                    
                    if dias_sin_evolucion:
                        glosa_evolucion = glosas_ref.get("evolucion_diaria", {})
                        valor_glosa_unitario = glosa_evolucion.get("valor_promedio_glosa", 150000)
                        valor_total = len(dias_sin_evolucion) * valor_glosa_unitario
                        
                        findings.append(Finding(
                            modulo=AuditModule.glosas,
                            descripcion=(
                                f"Días específicos sin evolución médica registrada: "
                                f"{', '.join(dias_sin_evolucion[:5])}{'...' if len(dias_sin_evolucion) > 5 else ''}. "
                                f"Total: {len(dias_sin_evolucion)} días."
                            ),
                            riesgo=RiskLevel.alto,
                            pagina=None,
                            recomendacion="Completar evoluciones médicas para las fechas indicadas.",
                            valor_glosa_estimado=valor_total,
                            normativa_aplicable="Resolución 1995 de 1999",
                            categoria="evolucion_diaria_fecha_especifica"
                        ))
            except Exception:
                pass  # Si no se pueden parsear fechas, ya se alertó arriba
    
    # 2. Verificar medicamentos sin orden médica
    glosa_medicamento = glosas_ref.get("orden_medicamento", {})
    valor_glosa_medicamento = glosa_medicamento.get("valor_promedio_glosa", 200000)
    
    medicamentos_sin_orden = []
    medicamentos_sin_indicacion = []
    
    for med in medicamentos:
        if not isinstance(med, dict):
            continue
        
        nombre_med = med.get("nombre", "sin nombre")
        
        # Compatibilidad con diferentes contratos de entrada:
        # 1) Esquema antiguo: incluye `orden_medica` explícita.
        # 2) Esquema del extractor: usa `nombre`/`dosis`/`frecuencia` sin `orden_medica`.
        tiene_orden = med.get("orden_medica")
        if tiene_orden is None:
            # Si no hay bandera explícita, inferir orden a partir de la presencia de
            # datos típicos de prescripción (dosis, frecuencia, vía, duración).
            campos_orden = ("dosis", "frecuencia", "via", "duracion")
            tiene_orden = any(
                bool(str(med.get(campo, "")).strip()) for campo in campos_orden
            )
        
        indicacion = med.get("indicacion", "")
        
        if not tiene_orden:
            medicamentos_sin_orden.append(nombre_med)
        
        # Solo auditar indicación cuando el campo está presente en el payload.
        if "indicacion" in med and (not indicacion or len(indicacion.strip()) < 5):
            medicamentos_sin_indicacion.append(nombre_med)
    
    if medicamentos_sin_orden:
        findings.append(Finding(
            modulo=AuditModule.glosas,
            descripcion=(
                f"Medicamentos sin orden médica documentada ({len(medicamentos_sin_orden)}): "
                f"{', '.join(medicamentos_sin_orden[:3])}{'...' if len(medicamentos_sin_orden) > 3 else ''}."
            ),
            riesgo=RiskLevel.alto,
            pagina=None,
            recomendacion=(
                "Documentar orden médica para cada medicamento administrado. "
                "Debe incluir: dosis, vía, frecuencia, duración y firma del médico."
            ),
            valor_glosa_estimado=len(medicamentos_sin_orden) * valor_glosa_medicamento,
            normativa_aplicable="Resolución 1403 de 2007 - Decreto 2200 de 2005",
            categoria="orden_medicamento_faltante"
        ))
    
    if medicamentos_sin_indicacion:
        findings.append(Finding(
            modulo=AuditModule.glosas,
            descripcion=(
                f"Medicamentos sin indicación clínica registrada ({len(medicamentos_sin_indicacion)}): "
                f"{', '.join(medicamentos_sin_indicacion[:3])}{'...' if len(medicamentos_sin_indicacion) > 3 else ''}."
            ),
            riesgo=RiskLevel.medio,
            pagina=None,
            recomendacion="Registrar indicación clínica que justifica la prescripción de cada medicamento.",
            valor_glosa_estimado=len(medicamentos_sin_indicacion) * 100000,
            normativa_aplicable="Resolución 1403 de 2007",
            categoria="medicamento_sin_indicacion"
        ))
    
    # 3. Verificar procedimientos sin consentimiento (ya cubierto en Módulo 3, aquí solo sumamos a glosa)
    glosa_consentimiento = glosas_ref.get("consentimiento_informado", {})
    valor_glosa_consentimiento = glosa_consentimiento.get("valor_promedio_glosa", 500000)
    
    procedimientos_sin_consentimiento = []
    for proc in procedimientos:
        if not isinstance(proc, dict):
            continue
        
        if not proc.get("consentimiento_firmado", False):
            procedimientos_sin_consentimiento.append(proc.get("nombre", "sin nombre"))
    
    if procedimientos_sin_consentimiento:
        findings.append(Finding(
            modulo=AuditModule.glosas,
            descripcion=(
                f"Procedimientos invasivos sin consentimiento informado ({len(procedimientos_sin_consentimiento)}): "
                f"{', '.join(procedimientos_sin_consentimiento)}."
            ),
            riesgo=RiskLevel.alto,
            pagina=None,
            recomendacion=(
                "Obtener y archivar consentimiento informado firmado. "
                "Alto riesgo legal y de glosa (Ley 23 de 1981)."
            ),
            valor_glosa_estimado=len(procedimientos_sin_consentimiento) * valor_glosa_consentimiento,
            normativa_aplicable="Ley 23 de 1981 - Ética Médica",
            categoria="consentimiento_faltante_critico"
        ))
    
    # 4. Verificar estudios sin resultados (cruce con Módulo 3)
    glosa_resultado = glosas_ref.get("resultado_pendiente", {})
    valor_glosa_resultado = glosa_resultado.get("valor_promedio_glosa", 180000)
    
    estudios_sin_resultado = []
    for estudio in estudios:
        if isinstance(estudio, dict) and not estudio.get("resultado_disponible", False):
            estudios_sin_resultado.append(estudio.get("nombre", "sin nombre"))
    
    if estudios_sin_resultado and len(estudios_sin_resultado) > 2:
        # Solo agregar si hay múltiples estudios pendientes
        findings.append(Finding(
            modulo=AuditModule.glosas,
            descripcion=(
                f"Múltiples estudios sin resultado documentado ({len(estudios_sin_resultado)}): "
                f"{', '.join(estudios_sin_resultado[:3])}{'...' if len(estudios_sin_resultado) > 3 else ''}."
            ),
            riesgo=RiskLevel.medio,
            pagina=None,
            recomendacion="Gestionar resultados pendientes antes del egreso. Posible glosa por estudios sin soporte.",
            valor_glosa_estimado=len(estudios_sin_resultado) * valor_glosa_resultado,
            normativa_aplicable="Resolución 1995 de 1999",
            categoria="resultados_pendientes_multiples"
        ))
    
    # 5. Calcular exposición total a glosas
    total_glosa_estimada = sum(
        f.valor_glosa_estimado for f in findings if f.valor_glosa_estimado
    )
    
    if total_glosa_estimada > 1000000:  # Más de 1 millón COP
        findings.append(Finding(
            modulo=AuditModule.glosas,
            descripcion=(
                f"⚠️ EXPOSICIÓN TOTAL A GLOSAS: ${total_glosa_estimada:,.0f} COP. "
                f"Identificadas {len(findings)} causas de glosa en este caso."
            ),
            riesgo=RiskLevel.alto,
            pagina=None,
            recomendacion=(
                "PRIORIDAD: Intervenir inmediatamente para mitigar riesgos de glosa. "
                "Coordinar con equipo médico para completar documentación faltante."
            ),
            normativa_aplicable="Normativa general del sistema de salud colombiano",
            categoria="exposicion_glosa_alta"
        ))
    
    return findings



# ============================================================================
# FUNCIONES DE CONSOLIDACIÓN Y ANÁLISIS
# ============================================================================

def run_all_modules(patient_data: dict) -> List[Finding]:
    """
    Ejecuta todos los módulos de auditoría y retorna hallazgos consolidados.
    
    Args:
        patient_data: Diccionario completo con datos del paciente
    
    Returns:
        Lista de hallazgos de todos los módulos
    """
    findings = []
    findings.extend(analyze_estancia(patient_data))
    findings.extend(analyze_cie10(patient_data))
    findings.extend(analyze_estudios(patient_data))
    findings.extend(analyze_glosas(patient_data))
    return findings


def calculate_risk(findings: List[Finding]) -> RiskLevel:
    """
    Calcula el nivel de riesgo global basado en los hallazgos.
    
    Lógica:
    - ALTO: Si hay 2+ hallazgos de riesgo alto O 1 hallazgo alto con glosa > $1M
    - MEDIO: Si hay hallazgos de riesgo medio O 1 hallazgo alto sin glosa crítica
    - BAJO: Solo hallazgos de riesgo bajo
    
    Args:
        findings: Lista de hallazgos (Finding)
    
    Returns:
        RiskLevel consolidado
    """
    if not findings:
        return RiskLevel.bajo
    
    alto_count = sum(1 for f in findings if f.riesgo == RiskLevel.alto)
    medio_count = sum(1 for f in findings if f.riesgo == RiskLevel.medio)
    
    # Calcular exposición total a glosas
    total_glosa = sum(
        f.valor_glosa_estimado for f in findings 
        if f.valor_glosa_estimado is not None
    )
    
    # Riesgo ALTO
    if alto_count >= 2:
        return RiskLevel.alto
    if alto_count >= 1 and total_glosa > 1000000:
        return RiskLevel.alto
    
    # Riesgo MEDIO
    if alto_count >= 1:
        return RiskLevel.medio
    if medio_count >= 2:
        return RiskLevel.medio
    if total_glosa > 500000:
        return RiskLevel.medio
    
    # Riesgo BAJO por defecto
    if medio_count == 0 and alto_count == 0:
        return RiskLevel.bajo
    
    return RiskLevel.medio  # Caso por defecto


def generate_audit_summary(findings: List[Finding], patient_data: dict) -> dict:
    """
    Genera un resumen ejecutivo de la auditoría.
    
    Args:
        findings: Lista de hallazgos
        patient_data: Datos del paciente
    
    Returns:
        Diccionario con resumen ejecutivo
    """
    # Calcular métricas
    total_findings = len(findings)
    riesgo_global = calculate_risk(findings)
    
    # Contar por nivel de riesgo
    alto_count = sum(1 for f in findings if f.riesgo == RiskLevel.alto)
    medio_count = sum(1 for f in findings if f.riesgo == RiskLevel.medio)
    bajo_count = sum(1 for f in findings if f.riesgo == RiskLevel.bajo)
    
    # Contar por módulo
    modulo_counts = {
        "estancia": sum(1 for f in findings if f.modulo == AuditModule.estancia),
        "cie10": sum(1 for f in findings if f.modulo == AuditModule.cie10),
        "estudios": sum(1 for f in findings if f.modulo == AuditModule.estudios),
        "glosas": sum(1 for f in findings if f.modulo == AuditModule.glosas),
    }
    
    # Calcular exposición total a glosas
    total_glosa = sum(
        f.valor_glosa_estimado for f in findings 
        if f.valor_glosa_estimado is not None
    )
    
    # Identificar hallazgos críticos (riesgo alto)
    hallazgos_criticos = [
        {
            "modulo": f.modulo.value,
            "descripcion": f.descripcion,
            "recomendacion": f.recomendacion,
            "valor_glosa": f.valor_glosa_estimado
        }
        for f in findings if f.riesgo == RiskLevel.alto
    ]
    
    # Extraer datos básicos del paciente
    paciente_info = {
        "diagnostico": patient_data.get("diagnostico_principal", "No especificado"),
        "codigo_cie10": patient_data.get("codigo_cie10", "No especificado"),
        "dias_hospitalizacion": patient_data.get("dias_hospitalizacion", 0)
    }
    
    return {
        "riesgo_global": riesgo_global.value,
        "total_hallazgos": total_findings,
        "hallazgos_por_riesgo": {
            "alto": alto_count,
            "medio": medio_count,
            "bajo": bajo_count
        },
        "hallazgos_por_modulo": modulo_counts,
        "exposicion_glosas_cop": total_glosa,
        "hallazgos_criticos": hallazgos_criticos[:5],  # Máximo 5 más importantes
        "paciente": paciente_info,
        "recomendacion_general": _generar_recomendacion_general(riesgo_global, total_glosa, alto_count)
    }


def _generar_recomendacion_general(riesgo: RiskLevel, glosa_total: float, hallazgos_altos: int) -> str:
    """Genera recomendación general basada en el análisis."""
    if riesgo == RiskLevel.alto:
        return (
            f"⚠️ CASO DE ALTA PRIORIDAD: Se identificaron {hallazgos_altos} hallazgos críticos "
            f"con exposición a glosas de ${glosa_total:,.0f} COP. "
            f"Requiere intervención inmediata del equipo de auditoría y coordinación médica."
        )
    elif riesgo == RiskLevel.medio:
        return (
            f"Caso requiere atención: Exposición a glosas de ${glosa_total:,.0f} COP. "
            f"Revisar documentación clínica y completar registros faltantes antes del egreso."
        )
    else:
        return (
            f"Documentación clínica adecuada con bajo riesgo de glosa. "
            f"Mantener estándares de calidad en el registro."
        )

