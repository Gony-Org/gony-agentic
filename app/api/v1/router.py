from fastapi import APIRouter
from app.api.v1.endpoints import agent, health  # Assuming health exists or just add agent

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
