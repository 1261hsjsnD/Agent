

class PromptBuilder:
    def __init__(self, session_manager, session_id: str, email: str):
        self.session_manager = session_manager
        self.session_id = session_id
        self.email = email

    async def builder_prompt(self, email: str, question: str) -> str:
        prompt = """
一: 角色：你是一个记忆提取助手
二: 任务：
      - 理解用户需求
      - 根据用户问题，提取相关记忆
三: 规则：
     - 你必须只输出最终回答，禁止输出 "Memory"、"Reply"、"用户姓名" 等任何标签或记忆复述。
"""
        prompt += f"用户问题：{question}\n"

        # 1. 窗口记忆（最近 N 条原文）
        window_memory = await self.session_manager.window_memory.query()
        if window_memory:
            prompt += "短期记忆-窗口记忆：\n"
            for i in window_memory:
                if i["role"] == "user":
                    prompt += f"用户提问：{i['content']}\n"
                else:
                    prompt += f"AI回复：{i['content']}\n"

        # 2. 摘要记忆
        summary_memory = await self.session_manager.summary_memory.query()
        if summary_memory:
            prompt += f"短期记忆-摘要记忆：{summary_memory}\n"

        # 3. 长期记忆（按 email 隔离的向量检索）
        long_memory = await self.session_manager.long_memory.query(email, question)
        if long_memory:
            prompt += "长期记忆：\n"
            for x in long_memory:
                prompt += f"{x}\n"

        # 4. 用户画像记忆（面试能力）
        profile_memory = await self.session_manager.profile_memory.query()
        if profile_memory:
            prompt += f"用户画像（面试能力）：{profile_memory}\n"

        return prompt
