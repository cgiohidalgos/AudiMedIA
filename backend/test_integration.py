"""
Script de prueba para validar la integración completa de módulos de auditoría
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.patient import PatientCase
from app.models.audit import AuditFinding
from app.services.ai.audit_modules import run_all_modules, calculate_risk, generate_audit_summary

# Caso de prueba: IAM con estancia prolongada
clinical_data = {
    "cama": "UCI-305",
    "edad": 68,
    "sexo": "M",
    "diagnostico_principal": "Infarto Agudo de Miocardio con elevación del ST de pared anterior",
    "codigo_cie10": "I21.0",
    "diagnosticos_secundarios": ["I25.1 Cardiopatía isquémica", "I10 Hipertensión arterial"],
    "fecha_ingreso": "2024-01-15",
    "dias_hospitalizacion": 18,
    "dias_esperados": 10,
    "medicamentos": [
        "Aspirina 100mg c/24h",
        "Atorvastatina 80mg c/24h",
        "Enalapril 10mg c/12h",
        "Metoprolol 50mg c/12h"
    ],
    "antecedentes": {
        "cardiovasculares": ["HTA desde hace 5 años"],
        "quirurgicos": []
    },
    "estudios_solicitados": [
        "Ecocardiograma - Resultado: pendiente",
        "Troponinas - Resultado: 8.5 ng/mL (elevadas)",
        "Radiografía de tórax - Indicación: no clara"
    ],
    "procedimientos": ["Cateterismo cardíaco con angioplastia"],
    "evoluciones": [
        {"fecha": "2024-01-15", "nota": "Ingreso por dolor torácico"},
        {"fecha": "2024-01-20", "nota": "Evolución favorable"}
    ]
}

async def test_integration():
    print("=" * 80)
    print("PRUEBA DE INTEGRACIÓN - MÓDULOS DE AUDITORÍA")
    print("=" * 80)
    
    # 1. Ejecutar módulos y obtener hallazgos
    print("\n1. Ejecutando módulos de auditoría...")
    findings = run_all_modules(clinical_data)
    risk_level = calculate_risk(findings)
    summary = generate_audit_summary(findings, clinical_data)
    
    print(f"   ✅ Ejecutados: {len(findings)} hallazgos encontrados")
    print(f"   ✅ Riesgo calculado: {risk_level.value.upper()}")
    print(f"   ✅ Resumen generado:")
    print(f"      - Riesgo global: {summary['riesgo_global']}")
    print(f"      - Total hallazgos: {summary['total_hallazgos']}")
    print(f"      - Exposición glosas: ${summary['exposicion_glosas_cop']:,.0f} COP")
    
    # 2. Simular guardado en base de datos
    print("\n2. Validando estructura de datos para guardado...")
    
    # Validar que el summary tiene todos los campos necesarios
    required_summary_fields = ["riesgo_global", "total_hallazgos", "exposicion_glosas_cop"]
    for field in required_summary_fields:
        if field not in summary:
            print(f"   ❌ ERROR: Falta campo '{field}' en summary")
            return
    print(f"   ✅ Summary tiene todos los campos requeridos")
    
    # Validar que los findings tienen todos los campos
    required_finding_fields = ["modulo", "categoria", "descripcion", "riesgo", 
                              "recomendacion", "normativa_aplicable", 
                              "valor_glosa_estimado", "pagina"]
    
    for i, finding in enumerate(findings):
        missing = [f for f in required_finding_fields if not hasattr(finding, f)]
        if missing:
            print(f"   ❌ Finding {i+1} falta campos: {missing}")
            return
    
    print(f"   ✅ Todos los {len(findings)} findings tienen campos completos")
    
    # 3. Mostrar ejemplo de datos que se guardarían
    print("\n3. Ejemplo de datos que se guardarían:")
    print(f"\n   PATIENT CASE:")
    print(f"   - diagnostico_principal: {clinical_data['diagnostico_principal']}")
    print(f"   - codigo_cie10: {clinical_data['codigo_cie10']}")
    print(f"   - riesgo_auditoria: {summary['riesgo_global']}")
    print(f"   - total_hallazgos: {summary['total_hallazgos']}")
    print(f"   - exposicion_glosas: {summary['exposicion_glosas_cop']}")
    print(f"   - audit_status: completed")
    
    print(f"\n   AUDIT FINDINGS (mostrando primeros 3):")
    for i, f in enumerate(findings[:3]):
        print(f"\n   Finding {i+1}:")
        print(f"   - modulo: {f.modulo.value}")
        print(f"   - categoria: {f.categoria}")
        print(f"   - descripcion: {f.descripcion[:80]}...")
        print(f"   - riesgo: {f.riesgo.value}")
        print(f"   - normativa_aplicable: {f.normativa_aplicable}")
        valor = f.valor_glosa_estimado if f.valor_glosa_estimado else 0
        print(f"   - valor_glosa_estimado: ${valor:,.0f} COP")
        print(f"   - estado: activo (default)")
    
    # 4. Verificar última ejecución en base de datos
    print("\n4. Verificando última entrada en base de datos...")
    async with AsyncSessionLocal() as db:
        # Obtener último paciente
        result = await db.execute(
            select(PatientCase).order_by(PatientCase.created_at.desc()).limit(1)
        )
        last_patient = result.scalar_one_or_none()
        
        if last_patient:
            print(f"   ✅ Último paciente encontrado:")
            print(f"      - ID: {last_patient.id}")
            print(f"      - Label: {last_patient.label}")
            print(f"      - Diagnóstico: {last_patient.diagnostico_principal}")
            print(f"      - Riesgo auditoría: {last_patient.riesgo_auditoria or 'NO ASIGNADO'}")
            print(f"      - Total hallazgos: {last_patient.total_hallazgos or 0}")
            print(f"      - Exposición glosas: ${last_patient.exposicion_glosas or 0:,.0f}")
            print(f"      - Audit status: {last_patient.audit_status or 'N/A'}")
            
            # Verificar hallazgos
            findings_result = await db.execute(
                select(AuditFinding)
                .where(AuditFinding.patient_id == last_patient.id)
                .limit(3)
            )
            db_findings = findings_result.scalars().all()
            
            if db_findings:
                print(f"\n   ✅ {len(db_findings)} hallazgos encontrados (mostrando primeros 3):")
                for f in db_findings:
                    print(f"      - {f.modulo}: {f.categoria or 'SIN CATEGORIA'}")
                    print(f"        Normativa: {f.normativa_aplicable or 'N/A'}")
                    print(f"        Glosa: ${f.valor_glosa_estimado or 0:,.0f}")
                    print(f"        Estado: {f.estado or 'N/A'}")
            else:
                print("   ⚠️  No se encontraron hallazgos asociados")
        else:
            print("   ⚠️  No hay pacientes en la base de datos aún")
    
    print("\n" + "=" * 80)
    print("PRUEBA COMPLETADA")
    print("=" * 80)
    print("\nPara probar con un PDF real:")
    print("1. Usar POST /api/v1/upload con un archivo PDF")
    print("2. Verificar GET /api/v1/patients/{id}/audit para ver el resumen")
    print("3. Usar PATCH /api/v1/patients/{id}/findings/{finding_id} para actualizar estado")

if __name__ == "__main__":
    asyncio.run(test_integration())
