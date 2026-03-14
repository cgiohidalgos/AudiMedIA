import requests
import time
import threading

def upload_and_wait():
    """Upload que espera para que puedas ver los logs del servidor"""
    
    print("🔥 PREPARANDO UPLOAD PARA MONITOREO DE LOGS...")
    print("📋 INSTRUCCIONES:")
    print("   1. Este script hará login")  
    print("   2. Esperará 10 segundos para que veas los logs del servidor")
    print("   3. Luego hará el upload")
    print("   4. Monitoreará el progreso")
    print("\n👀 ¡Observa los logs del servidor backend mientras esto corre!")
    print("=" * 60)
    
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
    print("✅ Login exitoso!")
    
    # Countdown
    print("\n⏰ Esperando para que puedas ver los logs del servidor...")
    for i in range(10, 0, -1):
        print(f"   ⏱️  Iniciando upload en {i} segundos...")
        time.sleep(1)
    
    print("\n🚀 ¡INICIANDO UPLOAD AHORA! (observa los logs del servidor)")
    
    # PDF simple pero válido
    pdf_content = b"""%PDF-1.4
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
/Length 120
>>
stream
BT
/F1 12 Tf
100 700 Td
(HISTORIA CLINICA TEST) Tj
0 -20 Td
(Paciente: Juan Perez) Tj
0 -20 Td  
(Edad: 45) Tj
0 -20 Td
(Diagnostico: Test) Tj
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
400
%%EOF"""
    
    files = {'files': ('historia_clinica_detallada.pdf', pdf_content, 'application/pdf')}
    
    try:
        upload_response = requests.post(
            'http://localhost:8000/api/v1/upload/',
            headers=headers,
            files=files,
            timeout=30
        )
        
        print(f"📊 UPLOAD RESPONSE: {upload_response.status_code}")
        
        if upload_response.status_code == 200:
            data = upload_response.json()
            session_id = data[0]['session_id']
            print(f"🎯 SESIÓN CREADA: {session_id}")
            print(f"💬 MENSAJE: {data[0]['message']}")
            
            # Monitorear por 2 minutos
            print("\n🔄 MONITOREANDO PROGRESO (2 minutos)...")
            for i in range(24):  # 24 checks de 5 segundos cada uno
                time.sleep(5)
                
                try:
                    status_response = requests.get(
                        f'http://localhost:8000/api/v1/upload/status/{session_id}',
                        headers=headers
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"📊 Check {i+1}: Status={status_data['status']}, Message={status_data.get('message', 'N/A')}")
                        
                        if status_data['status'] in ['completado', 'error']:
                            print(f"🏁 TERMINADO: {status_data['status']}")
                            break
                    else:
                        print(f"❌ Error checking status: {status_response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ Error en check: {e}")
            
        else:
            print(f"❌ Upload falló: {upload_response.status_code}")
            print(f"Response: {upload_response.text}")
            
    except Exception as e:
        print(f"💥 Error en upload: {e}")

if __name__ == "__main__":
    upload_and_wait()