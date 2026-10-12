from fastapi import APIRouter

from services.profile_service import upsert_profile, query_profile, StudentModel

profile_router = APIRouter()


@profile_router.post("/profile")
async def profile(student: StudentModel):
    return await upsert_profile(student)


@profile_router.get("/query")
async def profile_query(email: str):
    return await query_profile(email)
