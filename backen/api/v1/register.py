from fastapi import APIRouter

from api.schemas.auth import CreateUserSchema
from services.register_service import send_code, check_code, create_user

register_router = APIRouter()


@register_router.post('/register')
async def do_register(email: str):
    """发送注册验证码（邮箱作为 query 参数）"""
    return await send_code(email)


@register_router.get('/check')
async def do_check(email: str, code: str):
    """校验验证码，返回一次性注册凭证 ticket"""
    return await check_code(email, code)


@register_router.post('/create')
async def do_create(req: CreateUserSchema):
    """用注册凭证创建账号"""
    return await create_user(req.email, req.name, req.password, req.ticket)
