from fastapi import APIRouter

from app.api.v1 import demo, health, knowledge, rfq

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(demo.router)
api_router.include_router(rfq.router)
api_router.include_router(knowledge.router)
