from db.dao.postgres import get_pool


"""
用户画像记忆
专门读取「面试能力画像」（student.interview_ability 字段）

注意：本类只负责【读取】。
写入由面试评价流程负责（interview_evaluate_node -> career_db.update_interview_ability），
避免多处写入造成职责混乱。
"""


class ProfileMemory:
    def __init__(self, email: str):

        self.email = email

    async def query(self) -> str:
        """查询面试能力画像"""
        if not self.email:
            return ""
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT interview_ability FROM student WHERE email = %s",
                    (self.email,),
                )
                row = await cur.fetchone()
                return row[0] if row and row[0] else ""
