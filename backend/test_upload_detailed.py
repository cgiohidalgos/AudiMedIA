import requests
import time

print('🔥 TEST DEL SISTEMA - Activando logs detallados...')

try:
    # Login
    login_response = requests.post(
        'http://localhost:8002/api/v1/auth/login',
        json={'email': 'admin@audiomedia.co', 'password': 'Admin1234'}
    )
    
    print(f'🔑 Login: {login_response.status_code}')
    
    if login_response.status_code == 200:
        token = login_response.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Crear archivo PDF dummy
        dummy_pdf = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000120 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n180\n%%EOF'
        
        files = {'file': ('test-document.pdf', dummy_pdf, 'application/pdf')}
        
        print('📤 Subiendo PDF de prueba...')
        print('👀 Observa los logs en la otra terminal!')
        
        upload_response = requests.post(
            'http://localhost:8002/api/v1/upload',
            headers=headers,
            files=files,
            timeout=30
        )
        
        print(f'📊 Upload: {upload_response.status_code}')
        print(f'📝 Response: {upload_response.text[:200]}...')
        
    else:
        print(f'❌ Login falló: {login_response.text}')

except Exception as e:
    print(f'💥 Error: {e}')
    
print('✅ Test completado - ¡revisa los logs del servidor!')