import os
import json

from dotenv import load_dotenv

from db.dao.redis import get_redis

load_dotenv()

"""
短期记忆 - 窗口记忆（Redis list 存储最近 N 轮对话）

连接来自全局共享的 redis_client，不再每轮新建 / 关闭。
"""


class WindowMemory:
    def __init__(self, session_id: str):
        self.redis = get_redis()
        self.window_size = int(os.getenv("WINDOW_MEMORY_ROUNDS", "10"))
        self.session_id = session_id
        self.key = f"window_memory:{self.session_id}"
        self.count_key = f"window_memory_count:{self.session_id}"
        self.window_limit_time = int(os.getenv("WINDOW_MEMORY_TIME", "86400"))

    async def save(self, role: str, content: str):
        """保存一条消息到窗口记忆，并累计该会话的消息总数"""
        data = {"role": role, "content": content}
        await self.redis.rpush(self.key, json.dumps(data, ensure_ascii=False))
        # 只保留最近 window_size 条
        await self.redis.ltrim(self.key, -self.window_size, -1)
        # 设置过期时间
        await self.redis.expire(self.key, self.window_limit_time)

        # 累计消息总数：不随 ltrim 变化，供摘要 / 长期记忆触发判断
        # 与窗口 key 同寿命，避免 Redis 堆积无效计数 key
        await self.redis.incr(self.count_key)
        await self.redis.expire(self.count_key, self.window_limit_time)

    async def query(self) -> list:
        """查询窗口记忆（最近 window_size 条原文）"""
        if await self.redis.exists(self.key):
            data = await self.redis.lrange(self.key, 0, -1)
            return [json.loads(i) for i in data]
        return []

    async def total_count(self) -> int:
        """该会话累计写入的消息总数"""
        val = await self.redis.get(self.count_key)
        return int(val) if val else 0
