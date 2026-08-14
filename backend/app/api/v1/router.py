from fastapi import APIRouter

from app.api.v1.endpoints import auth, leaves, tickets, announcements, projects

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(leaves.router)
api_router.include_router(tickets.router)
api_router.include_router(announcements.router)
api_router.include_router(projects.router)
