"""
Script de prueba para módulos de auditoría clínica.

Ejecutar desde la raíz del backend:
    python test_audit_modules.py
"""

import sys
import json
from pathlib import Path

# Agregar directorio app al path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.ai.audit_modules import (
    run_all_modules,
    calculate_risk,
    generate_audit_summary,
    RiskLevel,
    AuditModule
)


def test_caso_iam():
    """Caso de prueba: IAM (Infarto Agudo de Miocardio) con estancia prolongada."""
    print("\n" + "=" * 80)
    print("CASO 1: IAM con estancia prolongada y documentación incompleta")
    print("=" * 80)
    
    patient_data = {
        "diagnostico_principal": "Infarto Agudo de Miocardio",
        "codigo_cie10": "I21.0",
        "dias_hospitalizacion": 12,  # Excede máximo de 7 días
        "en_uci": True,
        "fecha_ingreso": "2024-01-10",
        "sintomas": ["dolor torácico", "diaforesis", "disnea"],
        "examenes_realizados": ["Troponinas", "ECG", "Ecocardiograma"],
        "evoluciones": [
            {"fecha": "2024-01-10"},
            {"fecha": "2024-01-11"},
            {"fecha": "2024-01-12"},
            {"fecha": "2024-01-13"},
            # Faltan 8 evoluciones
        ],
        "medicamentos": [
            {"nombre": "Aspirina", "orden_medica": True, "indicacion": "Antiagregación plaquetaria"},
            {"nombre": "Atorvastatina", "orden_medica": False, "indicacion": ""},  # Sin orden
            {"nombre": "Metoprolol", "orden_medica": True, "indicacion": "Control FC"},
        ],
        "estudios_solicitados": [
            {"nombre": "TAC Cerebral", "resultado_disponible": False, "fecha_solicitud": "2024-01-15"},
            {"nombre": "Cateterismo", "resultado_disponible": True},
        ],
        "procedimientos_realizados": [
            {"nombre": "Cateterismo cardíaco", "consentimiento_firmado": True, "indicacion": "IAM con SDST"},
        ]
    }
    
    # Ejecutar módulos
    findings = run_all_modules(patient_data)
    riesgo = calculate_risk(findings)
    summary = generate_audit_summary(findings, patient_data)
    
    # Mostrar resultados
    print(f"\n📊 RESUMEN EJECUTIVO")
    print(f"Riesgo Global: {summary['riesgo_global'].upper()}")
    print(f"Total Hallazgos: {summary['total_hallazgos']}")
    print(f"Exposición a Glosas: ${summary['exposicion_glosas_cop']:,.0f} COP")
    print(f"\nHallazgos por riesgo:")
    for nivel, count in summary['hallazgos_por_riesgo'].items():
        print(f"  - {nivel.upper()}: {count}")
    
    print(f"\nHallazgos por módulo:")
    for modulo, count in summary['hallazgos_por_modulo'].items():
        if count > 0:
            print(f"  - {modulo}: {count}")
    
    print(f"\n💡 Recomendación General:")
    print(f"{summary['recomendacion_general']}")
    
    print(f"\n🔍 HALLAZGOS DETALLADOS ({len(findings)}):")
    for i, finding in enumerate(findings, 1):
        print(f"\n{i}. [{finding.modulo.value.upper()}] {finding.riesgo.value.upper()}")
        print(f"   {finding.descripcion}")
        print(f"   → Recomendación: {finding.recomendacion}")
        if finding.valor_glosa_estimado:
            print(f"   💰 Valor glosa: ${finding.valor_glosa_estimado:,.0f} COP")
        if finding.normativa_aplicable:
            print(f"   📋 Normativa: {finding.normativa_aplicable}")


def test_caso_apendicitis():
    """Caso de prueba: Apendicitis con documentación correcta."""
    print("\n" + "=" * 80)
    print("CASO 2: Apendicitis aguda con documentación adecuada")
    print("=" * 80)
    
    patient_data = {
        "diagnostico_principal": "Apendicitis aguda",
        "codigo_cie10": "K35.2",
        "dias_hospitalizacion": 3,  # Dentro del rango esperado
        "en_uci": False,
        "fecha_ingreso": "2024-01-15",
        "sintomas": ["dolor abdominal", "náuseas", "fiebre", "dolor fosa ilíaca derecha"],
        "examenes_realizados": ["Hemograma completo", "Ecografía abdominal", "TAC abdominopélvico"],
        "evoluciones": [
            {"fecha": "2024-01-15"},
            {"fecha": "2024-01-16"},
            {"fecha": "2024-01-17"},
        ],
        "medicamentos": [
            {"nombre": "Ceftriaxona", "orden_medica": True, "indicacion": "Profilaxis antibiótica"},
            {"nombre": "Metamizol", "orden_medica": True, "indicacion": "Analgesia"},
        ],
        "estudios_solicitados": [
            {"nombre": "Hemograma", "resultado_disponible": True},
            {"nombre": "Ecografía abdominal", "resultado_disponible": True},
        ],
        "procedimientos_realizados": [
            {
                "nombre": "Apendicectomía laparoscópica", 
                "consentimiento_firmado": True, 
                "indicacion": "Apendicitis aguda confirmada"
            },
        ]
    }
    
    # Ejecutar módulos
    findings = run_all_modules(patient_data)
    riesgo = calculate_risk(findings)
    summary = generate_audit_summary(findings, patient_data)
    
    # Mostrar resultados
    print(f"\n📊 RESUMEN EJECUTIVO")
    print(f"Riesgo Global: {summary['riesgo_global'].upper()}")
    print(f"Total Hallazgos: {summary['total_hallazgos']}")
    print(f"Exposición a Glosas: ${summary['exposicion_glosas_cop']:,.0f} COP")
    
    print(f"\n💡 Recomendación General:")
    print(f"{summary['recomendacion_general']}")
    
    if findings:
        print(f"\n🔍 HALLAZGOS ({len(findings)}):")
        for i, finding in enumerate(findings, 1):
            print(f"\n{i}. [{finding.modulo.value.upper()}] {finding.riesgo.value.upper()}")
            print(f"   {finding.descripcion}")
            print(f"   → {finding.recomendacion}")
    else:
        print("\n✅ No se identificaron hallazgos significativos.")


def test_caso_neumonia():
    """Caso de prueba: Neumonía con múltiples problemas de documentación."""
    print("\n" + "=" * 80)
    print("CASO 3: Neumonía con múltiples causas de glosa")
    print("=" * 80)
    
    patient_data = {
        "diagnostico_principal": "Neumonía bacteriana",
        "codigo_cie10": "J18",  # Sin 4to dígito
        "dias_hospitalizacion": 8,
        "en_uci": False,
        "fecha_ingreso": "2024-01-10",
        "sintomas": ["tos", "fiebre"],  # Faltan criterios mayores como infiltrado radiológico
        "examenes_realizados": ["Hemograma"],  # Faltan Rx tórax, gases arteriales, cultivo
        "evoluciones": [
            {"fecha": "2024-01-10"},
            {"fecha": "2024-01-12"},
            # Faltan 6 evoluciones
        ],
        "medicamentos": [
            {"nombre": "Ampicilina", "orden_medica": False, "indicacion": ""},  # Sin orden ni indicación
            {"nombre": "Omeprazol", "orden_medica": False, "indicacion": ""},
            {"nombre": "Salbutamol", "orden_medica": True, "indicacion": "Broncoespasmo"},
        ],
        "estudios_solicitados": [
            {"nombre": "Cultivo de esputo", "resultado_disponible": False, "fecha_solicitud": "2024-01-10"},
            {"nombre": "Gases arteriales", "resultado_disponible": False, "fecha_solicitud": "2024-01-11"},
        ],
        "procedimientos_realizados": []
    }
    
    # Ejecutar módulos
    findings = run_all_modules(patient_data)
    riesgo = calculate_risk(findings)
    summary = generate_audit_summary(findings, patient_data)
    
    # Mostrar resultados
    print(f"\n📊 RESUMEN EJECUTIVO")
    print(f"Riesgo Global: ⚠️ {summary['riesgo_global'].upper()}")
    print(f"Total Hallazgos: {summary['total_hallazgos']}")
    print(f"Exposición a Glosas: ${summary['exposicion_glosas_cop']:,.0f} COP")
    print(f"\nHallazgos por riesgo:")
    for nivel, count in summary['hallazgos_por_riesgo'].items():
        print(f"  - {nivel.upper()}: {count}")
    
    print(f"\n💡 Recomendación General:")
    print(f"{summary['recomendacion_general']}")
    
    print(f"\n🔍 HALLAZGOS CRÍTICOS:")
    for i, critico in enumerate(summary['hallazgos_criticos'], 1):
        print(f"\n{i}. [{critico['modulo'].upper()}]")
        print(f"   {critico['descripcion']}")
        print(f"   → {critico['recomendacion']}")
        if critico['valor_glosa']:
            print(f"   💰 ${critico['valor_glosa']:,.0f} COP")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PRUEBA DE MÓDULOS DE AUDITORÍA CLÍNICA")
    print("=" * 80)
    
    try:
        test_caso_iam()
        test_caso_apendicitis()
        test_caso_neumonia()
        
        print("\n" + "=" * 80)
        print("✅ PRUEBAS COMPLETADAS EXITOSAMENTE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR EN PRUEBAS: {e}")
        import traceback
        traceback.print_exc()
