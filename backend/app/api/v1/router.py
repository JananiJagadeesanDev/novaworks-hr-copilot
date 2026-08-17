from fastapi import APIRouter

from app.api.v1.endpoints import announcements, audit, auth, chat, leaves, projects, tickets

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(leaves.router)
api_router.include_router(tickets.router)
api_router.include_router(announcements.router)
api_router.include_router(projects.router)
api_router.include_router(chat.router)
api_router.include_router(audit.router)
