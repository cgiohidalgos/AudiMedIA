from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import engine, Base, AsyncSessionLocal
from app.db.seed import seed_default_users
import logging

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
for _noisy in ('httpx', 'httpcore', 'multipart'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
if settings.DEBUG:
    logging.getLogger('openai._base_client').setLevel(logging.DEBUG)
else:
    logging.getLogger('openai._base_client').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Importar modelos para que SQLAlchemy los registre (incluye DocumentChunk)
from app.models import user, patient, audit  # noqa: F401
from app.models.audit import DocumentChunk  # noqa: F401


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


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
