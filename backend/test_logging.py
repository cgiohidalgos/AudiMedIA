import requests
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

print("🔥 Test de logging - Activando endpoints...")

# 1. Test de login
login_data = {
    "email": "admin@audiomedia.co", 
    "password": "Admin1234"
}

print("🔑 Haciendo login...")
login_response = requests.post(
    f"{API_BASE}/api/v1/auth/login", 
    json=login_data
)
print(f"Login response: {login_response.status_code}")

if login_response.status_code != 200:
    print("❌ Login falló")
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Test de upload con archivo dummy
print("📄 Creando archivo PDF dummy...")
dummy_pdf_path = Path("test_dummy.pdf")
dummy_pdf_path.write_bytes(b"%PDF-1.4\nDummy PDF content for testing\n%%EOF")

# 3. Simular upload
print("📤 Simulando upload...")
try:
    with open(dummy_pdf_path, "rb") as f:
        files = {"file": ("test.pdf", f, "application/pdf")}
        upload_response = requests.post(
            f"{API_BASE}/api/v1/upload", 
            headers=headers,
            files=files,
            timeout=10
        )
    
    print(f"📊 Upload response status: {upload_response.status_code}")
    print(f"📊 Upload response: {upload_response.text[:200]}...")
    
except Exception as e:
    print(f"⚠️ Error en upload: {e}")

# Cleanup
dummy_pdf_path.unlink(missing_ok=True)
print("✅ Test completado - revisa los logs del backend!")