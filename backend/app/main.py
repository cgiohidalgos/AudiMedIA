import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import engine, Base, AsyncSessionLocal
from app.db.seed import seed_default_users

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Silenciar libs muy verbosas, excepto cuando estamos en modo DEBUG
for _noisy in ('httpx', 'httpcore', 'multipart'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

# Cuando se activa DEBUG, también queremos ver los logs HTTP del cliente OpenAI
if settings.DEBUG:
    logging.getLogger('openai._base_client').setLevel(logging.DEBUG)
else:
    logging.getLogger('openai._base_client').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Importar modelos para que SQLAlchemy los registre
from app.models import user, patient, audit  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas al iniciar (en producción usar Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Crear usuarios por defecto si no existen
    async with AsyncSessionLocal() as db:
        await seed_default_users(db)

    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug("→ %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        logger.debug("← %s %s %s", request.method, request.url.path, response.status_code)
        return response
    except Exception as exc:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
