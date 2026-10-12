from agent.memory.save.window_memory import WindowMemory
from agent.memory.save.summary_memory import SummaryMemory
from agent.memory.save.long_memory import LongMemory
from agent.memory.save.profile_memory import ProfileMemory
from agent.memory.manager.prompt_builder import PromptBuilder

"""
会话管理器：负责四层记忆的对象创建

user_key 说明：graph.py 传入的是 memory_user_id = email or str(user_id)，
有登录态时就是 email（长期记忆 / 画像记忆都按它定位）。
"""


class SessionManager:
    def __init__(self, session_id: str, email: str):
        self.window_memory = WindowMemory(session_id)
        self.session_id = session_id
        self.summary_memory = SummaryMemory(session_id)
        self.long_memory = LongMemory()
        self.profile_memory = ProfileMemory(email)
        self.prompt_builder = PromptBuilder(self, session_id, email)

    async def save(self, role: str, content: str):
        """添加窗口记忆"""
        await self.window_memory.save(role, content)

    async def build_prompt(self, email: str, question: str) -> str:
        """构建记忆提示词"""
        return await self.prompt_builder.builder_prompt(email, question)


