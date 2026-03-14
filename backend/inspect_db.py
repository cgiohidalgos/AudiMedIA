import sqlite3
import json
from datetime import datetime

def inspect_database():
    """Inspeccionar la base de datos para ver errores detallados"""
    
    print("🔍 INSPECCIONANDO BASE DE DATOS...")
    print("=" * 50)
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect('audiomedia.db')
        cursor = conn.cursor()
        
        print("📊 TABLAS EN LA BASE DE DATOS:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for table in tables:
            print(f"  📋 {table[0]}")
        
        print("\n🔍 SESIONES DE AUDITORÍA RECIENTES:")
        cursor.execute("""
            SELECT session_id, filename, status, created_at, updated_at, error_message 
            FROM auditoria_sesion 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        sessions = cursor.fetchall()
        
        if sessions:
            for session in sessions:
                session_id, filename, status, created_at, updated_at, error_message = session
                print(f"\n📋 SESSION: {session_id}")
                print(f"   📁 Archivo: {filename}")
                print(f"   ⭐ Status: {status}")
                print(f"   📅 Creada: {created_at}")
                print(f"   🔄 Actualizada: {updated_at}")
                print(f"   ❌ Error: {error_message or 'Sin error registrado'}")
        else:
            print("   📭 No hay sesiones registradas")
            
        print("\n🔍 CASOS DE PACIENTES RECIENTES:")
        cursor.execute("""
            SELECT id, label, audit_status, created_at 
            FROM patient_cases 
            ORDER BY created_at DESC 
            LIMIT 3
        """)
        cases = cursor.fetchall()
        
        for case in cases:
            case_id, label, audit_status, created_at = case
            print(f"   👤 {label} - Status: {audit_status} - {created_at}")
            
        print("\n🔍 REGISTROS DE AUDITORÍA (ERRORES):")
        cursor.execute("""
            SELECT COUNT(*) FROM audit_findings 
        """)
        findings_count = cursor.fetchone()[0]
        print(f"   📊 Total findings: {findings_count}")
        
        conn.close()
        print("\n✅ Inspección completada")
        
    except sqlite3.Error as e:
        print(f"❌ Error de base de datos: {e}")
    except Exception as e:
        print(f"💥 Error inesperado: {e}")

if __name__ == "__main__":
    inspect_database()