import sqlite3
import json

def inspect_database_structure():
    """Inspeccionar estructura de la base de datos y errores"""
    
    print("🔍 INSPECCIONANDO ESTRUCTURA DE BASE DE DATOS...")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect('audiomedia.db')
        cursor = conn.cursor()
        
        print("📊 ESTRUCTURA DE TABLA auditoria_sesion:")
        cursor.execute("PRAGMA table_info(auditoria_sesion);")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"   📋 {col[1]} ({col[2]}) - {col[3] and 'NOT NULL' or 'NULL OK'}")
            
        print("\n🔍 REGISTROS RECIENTES EN auditoria_sesion:")
        cursor.execute("SELECT * FROM auditoria_sesion ORDER BY created_at DESC LIMIT 3;")
        sessions = cursor.fetchall()
        
        # Obtener nombres de columnas
        col_names = [description[0] for description in cursor.description]
        print(f"   📋 Columnas: {col_names}")
        
        for i, session in enumerate(sessions, 1):
            print(f"\n   📋 REGISTRO {i}:")
            for j, value in enumerate(session):
                print(f"      {col_names[j]}: {value}")
                
        print("\n🔍 ESTRUCTURA DE TABLA patient_cases:")
        cursor.execute("PRAGMA table_info(patient_cases);")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"   📋 {col[1]} ({col[2]})")
            
        print("\n🔍 CASOS RECIENTES:")
        cursor.execute("SELECT id, label, audit_status, created_at FROM patient_cases ORDER BY created_at DESC LIMIT 2;")
        cases = cursor.fetchall()
        
        for case in cases:
            print(f"   👤 ID: {case[0]}, Label: {case[1]}, Status: {case[2]}, Fecha: {case[3]}")
            
        conn.close()
        print("\n✅ Inspección de estructura completada")
        
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    inspect_database_structure()