#!/usr/bin/env python3
"""
Script para ejecutar el servidor con logging visible y detallado
"""
import sys
import os
import logging
from pathlib import Path
import uvicorn

# Agregar el directorio backend al Python path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

def setup_detailed_logging():
    """Configurar logging detallado para debugging"""
    # Configurar el logger root con formato detallado
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S',
        force=True  # Force reconfiguration
    )
    
    # Configurar loggers específicos para nuestra app
    app_loggers = [
        'app.api.v1.endpoints.upload',
        'app.workers.pdf_worker', 
        'app.services.ai.extractor',
        'app.api.v1.endpoints.auth',
        'uvicorn.access'
    ]
    
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
    
    # Silenciar librerías muy verbosas
    for noisy in ('httpx', 'httpcore', 'aiosqlite', 'openai._base_client', 'multipart'):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    
    print("🔥 LOGGING DETALLADO ACTIVADO - Verás todos los pasos del upload!")

if __name__ == "__main__":
    print("🚀 Iniciando servidor AudiMedIA con logging VISIBLE...")
    print(f"📁 Directorio: {backend_dir}")
    print(f"🐍 Python path: {sys.path[0]}")
    print("=" * 70)
    
    # Configurar variables de entorno si es necesario
    os.environ.setdefault("PYTHONPATH", str(backend_dir))
    
    # Configurar logging detallado
    setup_detailed_logging()
    
    # Iniciar servidor con reload y logging visible
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
        access_log=True
    )