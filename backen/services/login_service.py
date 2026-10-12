import hashlib

import bcrypt
from dotenv import load_dotenv

from db.dao.postgres import get_pool

load_dotenv()

"""
登录服务

"""


def hash_password(password: str) -> str:
    """bcrypt 加盐哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored: str) -> bool:
    """校验密码

    兼容两种情况：
      - bcrypt 哈希（$2b$ 开头）：用 bcrypt 校验
      - 历史 sha256 哈希（64 位十六进制）：用 sha256 比对
    """
    if not stored:
        return False
    if stored.startswith("$2"):        # bcrypt
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
        except (ValueError, TypeError):
            return False
    # 兼容历史 sha256
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == stored


async def login(email: str, password: str) -> dict:
    """登录：查 student 表校验 email + password"""
    if not email or not password:
        return {"code": 400, "msg": "邮箱和密码不能为空"}

    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, password, name, email FROM student WHERE email = %s",
                (email,),
            )
            row = await cur.fetchone()

    if not row:
        return {"code": 404, "msg": "请检查邮箱"}

    stored_password = row[1]
    if not verify_password(password, stored_password):
        return {"code": 400, "msg": "密码错误"}

    # 历史 sha256 密码登录成功后，顺手升级为 bcrypt（平滑迁移）
    if stored_password and not stored_password.startswith("$2"):
        try:
            pool = get_pool()
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE student SET password = %s WHERE email = %s",
                        (hash_password(password), email),
                    )
        except Exception as e:
            print(f"密码升级失败（不影响登录）: {e}")

    # user_id 用于会话归属校验与记忆定位，前端登录后要存起来，每次聊天带上
    return {
        "code": 200,
        "msg": "登录成功",
        "user_id": str(row[0]),
        "email": row[3],
        "name": row[2] or "",
    }
