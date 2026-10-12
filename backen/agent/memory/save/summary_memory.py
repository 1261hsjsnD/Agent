

"""
短期记忆 - 摘要记忆（PostgreSQL 存储对话摘要）
"""
from db.dao.postgres import get_pool


class SummaryMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id

    async def save(self, summary: str):
        """保存/更新摘要"""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO conversation_summary(session_id, summary)
                    VALUES(%s, %s)
                    ON CONFLICT(session_id)
                    DO UPDATE SET summary = EXCLUDED.summary, update_time = NOW()
                    """,
                    (self.session_id, summary),
                )

    async def query(self) -> str:
        """查询摘要"""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT summary FROM conversation_summary WHERE session_id = %s",
                    (self.session_id,),
                )
                row = await cur.fetchone()
                return row[0] if row else ""
