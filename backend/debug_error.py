import requests
import json

def get_detailed_error():
    """Obtener detalles del error de la última sesión"""
    
    print("🔍 OBTENIENDO DETALLES DEL ERROR...")
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
    
    # Obtener lista de sesiones para ver la última
    try:
        # Probar diferentes endpoints para obtener info
        session_id = "bbac4a10-6d13-412b-bdee-d0917f26a62a"  # La sesión de arriba
        
        print(f"🔍 Consultando detalles de la sesión: {session_id}")
        status_response = requests.get(
            f'http://localhost:8000/api/v1/upload/status/{session_id}',
            headers=headers
        )
        
        if status_response.status_code == 200:
            data = status_response.json()
            print("📊 STATUS DETALLADO:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ No se pudo obtener status: {status_response.status_code}")
            print(f"Response: {status_response.text}")
            
        # Intentar obtener más info de la sesión
        print("\n🔍 Intentando obtener más información...")
        
        # Probar endpoint de sesiones en general
        sessions_response = requests.get(
            'http://localhost:8000/api/v1/patients',  # Endpoint de pacientes
            headers=headers,
            params={'limit': 5}
        )
        
        if sessions_response.status_code == 200:
            patients = sessions_response.json()
            print("👥 PACIENTES/SESIONES RECIENTES:")
            print(json.dumps(patients, indent=2, ensure_ascii=False)[:1000] + "...")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
    except Exception as e:
        print(f"💥 Error inesperado: {e}")

if __name__ == "__main__":
    get_detailed_error()