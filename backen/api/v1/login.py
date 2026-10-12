from fastapi import APIRouter

from api.schemas.auth import LoginSchema
from services.login_service import login

login_router = APIRouter()


@login_router.post('/login')
async def do_login(req: LoginSchema):
    """登录：校验邮箱密码，返回 user_id / email / name"""
    return await login(req.email, req.password)
