from fastapi import APIRouter

from api.v1.chat import chat_router
from api.v1.login import login_router
from api.v1.register import register_router
from api.v1.profile import profile_router
from api.v1.resume import resume_router

api_router = APIRouter()

api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(login_router, prefix="/login", tags=["Login"])
api_router.include_router(register_router, prefix="/login", tags=["Login"])
api_router.include_router(profile_router, prefix="/profile", tags=["Profile"])
api_router.include_router(resume_router, prefix="/resume", tags=["Resume"])
