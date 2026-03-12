"""
Script de migración para agregar campos de auditoría a la base de datos.

Este script agrega los nuevos campos necesarios para los módulos de auditoría:
- PatientCase: riesgo_auditoria, total_hallazgos, exposicion_glosas, audit_status
- AuditFinding: categoria, normativa_aplicable, valor_glosa_estimado, estado, fecha_resolucion, notas_resolucion, updated_at

Ejecutar desde la raíz del backend:
    python migrate_audit_fields.py
"""

import sqlite3
import os
from pathlib import Path

# Ruta a la base de datos
DB_PATH = Path(__file__).parent / "audiomedia.db"

def migrate():
    if not DB_PATH.exists():
        print(f"❌ Base de datos no encontrada en: {DB_PATH}")
        print("   Primero ejecuta el backend para crear la base de datos.")
        return False
    
    print(f"📦 Migrando base de datos: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # ============================================================
        # MIGRACIÓN 1: Agregar campos de auditoría a patient_cases
        # ============================================================
        print("\n✨ Agregando campos de auditoría a patient_cases...")
        
        # Verificar si ya existen los campos
        cursor.execute("PRAGMA table_info(patient_cases)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'riesgo_auditoria' not in columns:
            cursor.execute("ALTER TABLE patient_cases ADD COLUMN riesgo_auditoria VARCHAR(10)")
            print("   ✅ Agregado campo: riesgo_auditoria")
        else:
            print("   ⏭️  Campo riesgo_auditoria ya existe")
        
        if 'total_hallazgos' not in columns:
            cursor.execute("ALTER TABLE patient_cases ADD COLUMN total_hallazgos INTEGER DEFAULT 0")
            print("   ✅ Agregado campo: total_hallazgos")
        else:
            print("   ⏭️  Campo total_hallazgos ya existe")
        
        if 'exposicion_glosas' not in columns:
            cursor.execute("ALTER TABLE patient_cases ADD COLUMN exposicion_glosas REAL DEFAULT 0.0")
            print("   ✅ Agregado campo: exposicion_glosas")
        else:
            print("   ⏭️  Campo exposicion_glosas ya existe")
        
        if 'audit_status' not in columns:
            cursor.execute("ALTER TABLE patient_cases ADD COLUMN audit_status VARCHAR(20) DEFAULT 'pending'")
            print("   ✅ Agregado campo: audit_status")
        else:
            print("   ⏭️  Campo audit_status ya existe")
        
        # ============================================================
        # MIGRACIÓN 2: Agregar campos de auditoría a audit_findings
        # ============================================================
        print("\n✨ Agregando campos de auditoría a audit_findings...")
        
        cursor.execute("PRAGMA table_info(audit_findings)")
        findings_columns = [row[1] for row in cursor.fetchall()]
        
        if 'categoria' not in findings_columns:
            cursor.execute("ALTER TABLE audit_findings ADD COLUMN categoria VARCHAR(100)")
            print("   ✅ Agregado campo: categoria")
        else:
            print("   ⏭️  Campo categoria ya existe")
        
        if 'normativa_aplicable' not in findings_columns:
            cursor.execute("ALTER TABLE audit_findings ADD COLUMN normativa_aplicable VARCHAR(255)")
            print("   ✅ Agregado campo: normativa_aplicable")
        else:
            print("   ⏭️  Campo normativa_aplicable ya existe")
        
        if 'valor_glosa_estimado' not in findings_columns:
            cursor.execute("ALTER TABLE audit_findings ADD COLUMN valor_glosa_estimado REAL")
            print("   ✅ Agregado campo: valor_glosa_estimado")
        else:
            print("   ⏭️  Campo valor_glosa_estimado ya existe")
        
        if 'estado' not in findings_columns:
            cursor.execute("ALTER TABLE audit_findings ADD COLUMN estado VARCHAR(20) DEFAULT 'activo'")
            print("   ✅ Agregado campo: estado")
        else:
            print("   ⏭️  Campo estado ya existe")
        
        if 'fecha_resolucion' not in findings_columns:
            cursor.execute("ALTER TABLE audit_findings ADD COLUMN fecha_resolucion DATETIME")
            print("   ✅ Agregado campo: fecha_resolucion")
        else:
            print("   ⏭️  Campo fecha_resolucion ya existe")
        
        if 'notas_resolucion' not in findings_columns:
            cursor.execute("ALTER TABLE audit_findings ADD COLUMN notas_resolucion TEXT")
            print("   ✅ Agregado campo: notas_resolucion")
        else:
            print("   ⏭️  Campo notas_resolucion ya existe")
        
        if 'updated_at' not in findings_columns:
            cursor.execute("ALTER TABLE audit_findings ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            print("   ✅ Agregado campo: updated_at")
        else:
            print("   ⏭️  Campo updated_at ya existe")
        
        conn.commit()
        print("\n✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("\n📊 Estructura actualizada:")
        
        # Mostrar estructura final
        cursor.execute("PRAGMA table_info(patient_cases)")
        print("\n   patient_cases:")
        for row in cursor.fetchall():
            print(f"     - {row[1]} ({row[2]})")
        
        cursor.execute("PRAGMA table_info(audit_findings)")
        print("\n   audit_findings:")
        for row in cursor.fetchall():
            print(f"     - {row[1]} ({row[2]})")
        
        return True
        
    except sqlite3.Error as e:
        print(f"\n❌ ERROR durante la migración: {e}")
        conn.rollback()
        return False
    
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("=" * 80)
    print("MIGRACIÓN DE CAMPOS DE AUDITORÍA CLÍNICA")
    print("=" * 80)
    
    success = migrate()
    
    if success:
        print("\n" + "=" * 80)
        print("✅ Base de datos lista para los módulos de auditoría")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ Migración falló - revisar errores arriba")
        print("=" * 80)
