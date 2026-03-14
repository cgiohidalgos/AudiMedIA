#!/usr/bin/env python3
"""
Servidor con logging ULTRA VISIBLE para debugging
"""
import sys
import os
import logging
from pathlib import Path
import uvicorn
from datetime import datetime

# Agregar el directorio backend al Python path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

def setup_ultra_visible_logging():
    """Configurar logging ULTRA visible para debugging"""
    # Limpiar todos los loggers existentes
    logging.getLogger().handlers.clear()
    
    # Configurar formato super claro
    class ColoredFormatter(logging.Formatter):
        def format(self, record):
            # Agregar emoji según el nivel
            emoji_map = {
                'DEBUG': '🔍',
                'INFO': '📝', 
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }
            emoji = emoji_map.get(record.levelname, '📝')
            
            # Formato visible
            timestamp = datetime.now().strftime('%H:%M:%S')
            return f"{emoji} {timestamp} | {record.levelname:8} | {record.name:30} | {record.getMessage()}"
    
    # Configurar handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    
    # Configurar logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # Configurar loggers específicos para nuestra app - MUY VISIBLE
    important_loggers = [
        'app.api.v1.endpoints.upload',
        'app.workers.pdf_worker', 
        'app.services.ai.extractor',
        'app.api.v1.endpoints.auth',
        'uvicorn.access',
        'app.main'
    ]
    
    for logger_name in important_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = True  # Asegurar que se propague al root
    
    # Silenciar librerías MUY verbosas
    for noisy in ('httpx', 'httpcore', 'aiosqlite', 'multipart', 'openai._base_client'):
        logging.getLogger(noisy).setLevel(logging.ERROR)  # Solo errores
    
    print("🔥🔥🔥 LOGGING ULTRA VISIBLE ACTIVADO 🔥🔥🔥")
    print("💡 Ahora verás TODOS los logs de upload paso a paso!")
    print("🎯 Sube un PDF y observa esta consola!")
    print("=" * 60)

def create_debug_app():
    """Crear app FastAPI con configuración de debug y CORS"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.main import lifespan
    from app.api.v1.router import api_router
    from app.core.config import settings
    
    app = FastAPI(
        title=f"{settings.APP_NAME} - DEBUG MODE",
        version=f"{settings.APP_VERSION}-debug",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS ULTRA PERMISIVO para resolver problema definitivamente
    debug_origins = ["*"]  # Permitir TODOS los orígenes

    app.add_middleware(
        CORSMiddleware,
        allow_origins=debug_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )

    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Middleware adicional para debugging CORS
    @app.middleware("http")
    async def cors_debug_middleware(request, call_next):
        print(f"🌐 REQUEST: {request.method} {request.url} from {request.headers.get('origin', 'no-origin')}")
        
        response = await call_next(request)
        
        # Forzar headers CORS en todas las respuestas
        response.headers["Access-Control-Allow-Origin"] = "*"  
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        print(f"🔄 RESPONSE: {response.status_code} with CORS headers added")
        return response
    
    print(f"🌐 CORS configurado para: ULTRA PERMISIVO (*) + middleware forzado")
    
    return app

if __name__ == "__main__":
    print("🚀 SERVIDOR AUDIOMEDIA - MODO DEBUG ULTRA VISIBLE")
    print(f"📁 Directorio: {backend_dir}")
    print("=" * 60)
    
    # Configurar Python path
    os.environ.setdefault("PYTHONPATH", str(backend_dir))
    
    # Configurar logging ultra visible
    setup_ultra_visible_logging()
    
    # Crear app con CORS debug
    app = create_debug_app()
    
    # Iniciar servidor
    print("🎬 Iniciando servidor... Los logs aparecerán aquí!")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        reload=False,  # Disable reload para logs más claros
        log_level="debug",
        access_log=True,
        use_colors=False  # Evitar conflictos de colores
    )