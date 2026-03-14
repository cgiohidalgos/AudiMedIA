import requests
import time

print('🔸 Haciendo request para activar logs...')
try:
    response = requests.get('http://localhost:8000/health')
    print(f'Health check: {response.status_code}')
    
    # Hacer login
    login_data = {'email': 'admin@audiomedia.co', 'password': 'Admin1234'}
    login_response = requests.post('http://localhost:8000/api/v1/auth/login', json=login_data)
    print(f'Login: {login_response.status_code}')
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        headers = {'Authorization': f'Bearer {token}'}
        
        # Probar endpoint de patients
        patients_response = requests.get('http://localhost:8000/api/v1/patients', headers=headers)
        print(f'Patients: {patients_response.status_code}')
        print(f'Patients data: {patients_response.text[:100]}...')
    
    print('✅ Requests completados - deberían aparecer logs!')
except Exception as e:
    print(f'Error: {e}')