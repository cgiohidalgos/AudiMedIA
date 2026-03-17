from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, upload, patients, chat, dashboard, demo, documents, processing, recommendations, config, notifications

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(upload.router)
api_router.include_router(processing.router)
api_router.include_router(patients.router)
api_router.include_router(chat.router)
api_router.include_router(dashboard.router)
api_router.include_router(demo.router)
api_router.include_router(documents.router)
api_router.include_router(recommendations.router)
api_router.include_router(config.router)
api_router.include_router(notifications.router)
