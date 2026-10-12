import contextlib
import json
import time
import uuid
import os
from dotenv import load_dotenv
load_dotenv()

from redis.asyncio import Redis

"""
会话服务：会话的创建 / 校验，以及基于 Redis 的分布式会话锁

1. 会话校验：确认 session 存在且归属当前用户，防止伪造 session_id 读到别人的记忆。
2. 会话锁：同一 session 同一时刻只允许一个请求在执行，避免两条流同时读写
   同一份窗口记忆和 LangGraph checkpoint 造成状态错乱。

锁用 Redis 实现（而不是内存锁）
会话元数据也存 Redis
"""
# 会话不存在的固定原因串，调用方据此判断"要不要自动创建"
SESSION_NOT_FOUND = "会话不存在"

class SessionBusyError(RuntimeError):
    """抢不到会话锁：上一条消息还没处理完"""


class SessionService:
    def __init__(self, redis: Redis):
        self.redis = redis

    # ---------------- 会话创建 / 校验 ----------------

    def _key(self, session_id: str) -> str:
        """会话在 Redis 中的键"""
        return f"session:{session_id}"

    async def create_session(self, user_id: str, session_id: str | None = None) -> str:
        """
        创建会话。
        - 不传 session_id：生成 uuid 作为新会话 id
        - 传了 session_id：用指定的 id 建会话（兼容调用方使用固定 id 的场景）
        返回纯 session_id（不含前缀）
        """
        sid = session_id or uuid.uuid4().hex
        data = {"user_id": str(user_id), "create_time": time.time()}
        await self.redis.set(
            self._key(sid), json.dumps(data, ensure_ascii=False), ex=int(os.getenv("SESSION_TTL"))
        )
        return sid

    async def check_session(self, user_id: str, session_id: str):
        """
        校验会话是否存在且归属该用户
        返回 (是否通过, 原因)
        """
        if not session_id:
            return False, "会话 id 为空"

        data = await self.redis.get(self._key(session_id))
        if not data:
            return False, SESSION_NOT_FOUND

        try:
            info = json.loads(data)
        except (TypeError, ValueError):
            return False, "会话数据异常"

        if str(info.get("user_id")) != str(user_id):
            return False, "会话不属于该用户"

        return True, "会话存在且归属该用户"

    # ---------------- 分布式会话锁 ----------------

    @contextlib.asynccontextmanager
    async def session_lock(self, session_id: str, ttl_ms: int = 5 * 60 * 1000):
        """
        同一 session 的互斥锁。
        - nx=True：只有 key 不存在才能设置成功
        - px=ttl_ms：带过期时间，进程崩溃也不会永久死锁
        - 释放时用 Lua 比对 token 再删除，防止误删别人的锁
        """
        key = f"lock:session:{session_id}"
        token = uuid.uuid4().hex

        ok = await self.redis.set(key, token, nx=True, px=ttl_ms)
        if not ok:
            raise SessionBusyError("会话忙，上一条消息还没处理完，请稍后再试")

        try:
            yield
        finally:
            lua = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            else
                return 0
            end
            """
            try:
                await self.redis.eval(lua, 1, key, token)
            except Exception:
                # 释放失败不影响主流程，锁有过期时间兜底
                pass
