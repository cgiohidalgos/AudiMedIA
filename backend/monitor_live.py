import requests
import time
import json

def test_and_monitor():
    """Hacer requests y mostrar lo que pasa en tiempo real"""
    
    print("🔥 INICIANDO MONITOREO EN VIVO...")
    print("=" * 50)
    
    # Login
    print("🔑 Haciendo login...")
    login_response = requests.post(
        'http://localhost:8000/api/v1/auth/login',
        json={'email': 'admin@audiomedia.co', 'password': 'Admin1234'}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login falló: {login_response.status_code}")
        return
    
    token = login_response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print(f"✅ Login exitoso!")
    
    # Crear archivo PDF dummy más realista
    dummy_pdf = b'''%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Historia Clinica de Prueba) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000120 00000 n 
0000000230 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
320
%%EOF'''
    
    print("📤 Subiendo PDF de prueba...")
    print("👀 Observando respuesta del servidor...")
    
    # Upload con el formato correcto
    files = {'files': ('historia_prueba.pdf', dummy_pdf, 'application/pdf')}
    upload_response = requests.post(
        'http://localhost:8000/api/v1/upload/',  # Nota la barra final
        headers=headers,
        files=files,
        timeout=30
    )
    
    print(f"📊 Upload Response: {upload_response.status_code}")
    if upload_response.status_code == 200:
        data = upload_response.json()
        print(f"📋 Respuesta: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Si hay session_id, monitorear progreso
        if 'session_id' in str(data):
            session_id = None
            try:
                if isinstance(data, list) and len(data) > 0:
                    session_id = data[0].get('session_id')
                elif isinstance(data, dict):
                    session_id = data.get('session_id')
                    
                if session_id:
                    print(f"🔍 Monitoreando progreso de sesión: {session_id}")
                    monitor_progress(session_id, headers)
            except Exception as e:
                print(f"⚠️ Error obteniendo session_id: {e}")
    else:
        print(f"❌ Upload falló: {upload_response.text[:500]}")

def monitor_progress(session_id, headers):
    """Monitorear el progreso de una sesión"""
    print("🔄 Iniciando monitoreo de progreso...")
    
    for i in range(30):  # Máximo 30 checks (5 minutos)
        try:
            status_response = requests.get(
                f'http://localhost:8000/api/v1/upload/status/{session_id}',
                headers=headers,
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"📊 Check {i+1}: {json.dumps(status_data, indent=2, ensure_ascii=False)}")
                
                # Si está completo, terminar
                if status_data.get('status') in ['completado', 'error']:
                    print(f"🏁 Procesamiento terminado: {status_data.get('status')}")
                    break
            else:
                print(f"⚠️ Error checking status: {status_response.status_code}")
                
        except Exception as e:
            print(f"❌ Error en monitoreo: {e}")
            
        print(f"⏰ Esperando 10 segundos... (check {i+1}/30)")
        time.sleep(10)

if __name__ == "__main__":
    test_and_monitor()