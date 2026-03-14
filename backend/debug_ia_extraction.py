import requests
import json

def debug_ia_extraction():
    """Debug específico para ver qué pasa en la extracción de IA"""
    
    print("🔍 DEBUG ESPECÍFICO - EXTRACTOR DE IA")
    print("=" * 50)
    
    # Login
    login_response = requests.post(
        'http://localhost:8000/api/v1/auth/login',
        json={'email': 'admin@audiomedia.co', 'password': 'Admin1234'}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login falló: {login_response.status_code}")
        return
    
    token = login_response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # PDF con contenido médico más realista
    pdf_contenido_medico = b"""%PDF-1.4
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
/Length 800
>>
stream
BT
/F1 12 Tf
50 750 Td
(INSTITUTO CARDIOVASCULAR DE COLOMBIA) Tj
0 -30 Td
(HISTORIA CLINICA No: HC-2024-001234) Tj
0 -20 Td
(FECHA: 13/03/2026) Tj
0 -40 Td
(DATOS DEL PACIENTE:) Tj
0 -15 Td
(Nombre: MARIA GONZALEZ RODRIGUEZ) Tj
0 -15 Td
(Cedula: 52.123.456) Tj
0 -15 Td
(Edad: 67 anos) Tj
0 -15 Td
(Sexo: Femenino) Tj
0 -15 Td
(Fecha de Nacimiento: 15/08/1956) Tj
0 -15 Td
(Cama: 302-A) Tj
0 -30 Td
(HOSPITALIZACION:) Tj
0 -15 Td
(Fecha de Ingreso: 10/03/2026) Tj
0 -15 Td
(Fecha de Egreso: 13/03/2026) Tj
0 -15 Td
(Dias de Estancia: 3 dias) Tj
0 -15 Td
(Dias Esperados Segun DRG: 5 dias) Tj
0 -30 Td
(DIAGNOSTICOS:) Tj
0 -15 Td
(Diagnostico Principal: Infarto Agudo de Miocardio) Tj
0 -15 Td
(Codigo CIE-10: I21.9) Tj
0 -15 Td
(Diagnosticos Secundarios: Hipertension Arterial K90.9, Diabetes Mellitus E11.9) Tj
0 -30 Td
(MEDICAMENTOS:) Tj
0 -15 Td
(- Atorvastatina 40mg cada 24 horas) Tj
0 -15 Td
(- Metoprolol 50mg cada 12 horas) Tj
0 -15 Td
(- Aspirina 100mg cada 24 horas) Tj
0 -15 Td
(- Metformina 850mg cada 12 horas) Tj
0 -30 Td
(PROCEDIMIENTOS:) Tj
0 -15 Td
(- Cateterismo cardiaco diagnostico - Fecha: 11/03/2026) Tj
0 -15 Td
(- Angioplastia coronaria - Fecha: 11/03/2026) Tj
0 -30 Td
(ESTUDIOS SOLICITADOS:) Tj
0 -15 Td
(- Electrocardiograma de 12 derivaciones) Tj
0 -15 Td
(- Troponinas I seriadas) Tj
0 -15 Td
(- Perfil lipidico completo) Tj
0 -15 Td
(- Hemoglobina glicosilada) Tj
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
1100
%%EOF"""
    
    print("📤 Subiendo PDF con contenido médico realista...")
    files = {'files': ('historia_clinica_completa.pdf', pdf_contenido_medico, 'application/pdf')}
    
    try:
        upload_response = requests.post(
            'http://localhost:8000/api/v1/upload/',
            headers=headers,
            files=files,
            timeout=30
        )
        
        if upload_response.status_code == 200:
            data = upload_response.json()
            session_id = data[0]['session_id']
            print(f"🎯 SESIÓN CREADA: {session_id}")
            
            # Monitorear con más detalle
            print("\n🔄 MONITOREANDO EXTRACCIÓN DE IA...")
            for i in range(60):  # Monitor por 5 minutos
                try:
                    status_response = requests.get(
                        f'http://localhost:8000/api/v1/upload/status/{session_id}',
                        headers=headers
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"📊 Check {i+1}: Status={status_data['status']}")
                        
                        # Si está listo, obtener detalles del paciente creado
                        if status_data['status'] == 'listo':
                            print("✅ ¡PROCESAMIENTO COMPLETADO!")
                            
                            # Obtener lista de pacientes para ver si se creó
                            patients_response = requests.get(
                                'http://localhost:8000/api/v1/patients',
                                headers=headers,
                                params={'limit': 1}
                            )
                            
                            if patients_response.status_code == 200:
                                patients = patients_response.json()
                                if patients:
                                    print("👤 PACIENTE CREADO:")
                                    patient = patients[0]
                                    for key, value in patient.items():
                                        if value and value != 'N/A':
                                            print(f"   {key}: {value}")
                                else:
                                    print("❌ No se creó ningún paciente")
                            break
                            
                        elif status_data['status'] == 'error':
                            print("❌ ERROR EN PROCESAMIENTO")
                            break
                            
                        elif i < 59:  # No imprimir en la última iteración
                            print(f"⏰ Esperando... (5s)")
                            
                    else:
                        print(f"⚠️ Error status: {status_response.status_code}")
                        
                except Exception as e:
                    print(f"❌ Error en check: {e}")
                    
                if i < 59:  # No sleep en la última iteración
                    import time
                    time.sleep(5)
                    
        else:
            print(f"❌ Upload falló: {upload_response.status_code}")
            print(f"Response: {upload_response.text}")
            
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    debug_ia_extraction()