from fastapi import APIRouter

from app.api.v1 import auth, demo, health, knowledge, knowledge_debug, rfq

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(demo.router)
api_router.include_router(rfq.router)
api_router.include_router(knowledge.router)
api_router.include_router(knowledge_debug.router)
