import asyncio
import os
import random
import smtplib
import uuid
from email.mime.text import MIMEText

from dotenv import load_dotenv

from db.dao.postgres import get_pool
from db.dao.redis import get_redis
from services.login_service import hash_password

load_dotenv()

"""
注册服务

采用「邮箱验证码」三步流程（不使用 JWT）：
  1. send_code(email)          发验证码（Redis 存 60 秒）
  2. check_code(email, code)   校验验证码 -> 返回一次性注册凭证 ticket
  3. create_user(...)          校验 ticket -> 创建账号

一次性凭证用 Redis 实现（UUID + 300 秒过期 + 用后即删），
替代 JWT 的「防重放 / 防伪造」作用。
"""

# 验证码有效期（秒）
CODE_TTL = 60
# 注册凭证有效期（秒）—— 给用户留出填写用户名/密码的时间
TICKET_TTL = 300
# Redis key 前缀
_CODE_KEY = "reg_code:"
_TICKET_KEY = "reg_ticket:"


async def _email_exists(email: str) -> bool:
    """检查邮箱是否已注册"""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT email FROM student WHERE email = %s", (email,))
            return await cur.fetchone() is not None


def _send_email(email: str, code: str) -> None:
    """通过 SMTP 发送验证码邮件（QQ 邮箱 465 端口使用 SSL）

    这是同步阻塞操作，调用方用 asyncio.to_thread 包一层，避免阻塞事件循环。
    """
    sender = os.getenv("SENDER_EMAIL")
    psw = os.getenv("SENDER_EMAIL_PASSWORD")
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "465"))

    message = MIMEText(
        f"您正在注册 AI 职业规划系统账号，验证码是：{code}，请在 60 秒内输入。",
        _subtype="plain",
        _charset="utf-8",
    )
    message["From"] = sender
    message["To"] = email
    message["Subject"] = "注册验证码"

    # 465 端口用 SMTP_SSL，587 端口用 SMTP + starttls
    if port == 465:
        smtp = smtplib.SMTP_SSL(host=host, port=port, timeout=10)
    else:
        smtp = smtplib.SMTP(host=host, port=port, timeout=10)
        smtp.starttls()
    try:
        smtp.login(sender, psw)
        smtp.sendmail(sender, [email], message.as_string())
    finally:
        smtp.quit()


async def send_code(email: str) -> dict:
    """发送注册验证码"""
    if not email:
        return {"code": 400, "msg": "邮箱不能为空"}

    # 1. 已注册的邮箱不发
    if await _email_exists(email):
        return {"code": 400, "msg": "该邮箱已被注册"}

    # 2. 生成 4 位验证码
    code = "".join(str(random.randint(0, 9)) for _ in range(4))

    # 3. 发邮件（同步操作丢线程池）
    try:
        await asyncio.to_thread(_send_email, email, code)
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return {"code": 500, "msg": f"验证码发送失败: {e}"}

    # 4. 存 Redis（60 秒过期）
    redis = get_redis()
    await redis.set(f"{_CODE_KEY}{email}", code, ex=CODE_TTL)

    return {"code": 200, "msg": "验证码已发送，请查收邮件", "email": email}


async def check_code(email: str, code: str) -> dict:
    """校验验证码，通过后返回一次性注册凭证 ticket"""
    if not email or not code:
        return {"code": 400, "msg": "邮箱和验证码不能为空"}

    redis = get_redis()
    stored = await redis.get(f"{_CODE_KEY}{email}")
    if not stored:
        return {"code": 404, "msg": "验证码已过期，请重新获取"}

    if str(stored).strip() != str(code).strip():
        return {"code": 400, "msg": "验证码错误"}

    # 校验通过：删除验证码（一次性）
    await redis.delete(f"{_CODE_KEY}{email}")

    # 生成一次性注册凭证（300 秒有效）
    ticket = uuid.uuid4().hex
    await redis.set(f"{_TICKET_KEY}{ticket}", email, ex=TICKET_TTL)

    return {"code": 200, "msg": "验证成功", "ticket": ticket}


async def create_user(email: str, name: str, password: str, ticket: str) -> dict:
    """用注册凭证创建账号"""
    if not email or not password or not ticket:
        return {"code": 400, "msg": "邮箱、密码、验证凭证不能为空"}

    # 1. 校验凭证是否有效（未被使用 / 未过期）
    redis = get_redis()
    t_email = await redis.get(f"{_TICKET_KEY}{ticket}")
    if not t_email:
        return {"code": 401, "msg": "验证已失效，请重新验证邮箱"}

    # 2. 凭证里的邮箱必须与提交的一致
    if str(t_email) != email:
        return {"code": 401, "msg": "邮箱与验证邮箱不一致，请重新验证"}

    # 3. 销毁凭证（只能用一次，防重放）
    await redis.delete(f"{_TICKET_KEY}{ticket}")

    # 4. 入库
    pool = get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT email FROM student WHERE email = %s", (email,))
                if await cur.fetchone():
                    return {"code": 400, "msg": "该邮箱已被注册"}

                await cur.execute(
                    "INSERT INTO student (email, name, password) VALUES (%s, %s, %s) RETURNING id",
                    (email, name or "", hash_password(password)),
                )
                row = await cur.fetchone()
        return {
            "code": 200,
            "msg": "注册成功",
            "user_id": str(row[0]) if row else "",
        }
    except Exception as e:
        return {"code": 500, "msg": f"注册失败: {e}"}
