#!/usr/bin/env python3
"""
Servidor ESPECÍFICO para resolver el problema CORS del chat
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

def setup_logging():
    """Configurar logging simple"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_cors_fixed_app():
    """Crear app FastAPI con CORS ULTRA ESPECÍFICO para chat"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.main import lifespan
    from app.api.v1.router import api_router
    from app.core.config import settings
    
    app = FastAPI(
        title=f"{settings.APP_NAME} - CORS FIXED",
        version=f"{settings.APP_VERSION}-cors-fix",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS ESPECÍFICO para solucionar el problema
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True, 
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"]
    )

    # Middleware ESPECÍFICO para chat endpoint
    from fastapi import Request, Response
    from fastapi.responses import JSONResponse
    
    @app.middleware("http")
    async def chat_cors_fix_middleware(request: Request, call_next):
        # Log de la request
        origin = request.headers.get("origin")
        print(f"🌐 {request.method} {request.url.path} from origin: {origin}")
        
        # Manejar preflight OPTIONS específicamente
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        # Procesar request normal
        try:
            response = await call_next(request)
        except Exception as e:
            print(f"❌ Error procesando {request.method} {request.url.path}: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Server error: {str(e)}"},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        # Forzar headers CORS en TODAS las respuestas
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*" 
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        print(f"✅ {request.method} {request.url.path} -> {response.status_code}")
        return response

    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    print("🎯 CORS FIXED SERVER - Configuración específica para resolver el problema del chat")
    return app

if __name__ == "__main__":
    print("🚀 SERVIDOR CORS FIXED - Puerto 8005")
    print("🎯 Específicamente diseñado para resolver error CORS del chat")
    print("=" * 60)
    
    # Configurar Python path
    os.environ.setdefault("PYTHONPATH", str(backend_dir))
    
    # Configurar logging
    setup_logging()
    
    # Crear app con CORS arreglado
    app = create_cors_fixed_app()
    
    # Iniciar servidor en puerto diferente
    print("🎬 Iniciando servidor CORS FIXED en puerto 8005...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8005,
        reload=False,
        log_level="info",
        access_log=True
    )