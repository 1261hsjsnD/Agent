from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from agent.memory.save.long_memory import LongMemory
from agent.prompts.builder_prompt import BuilderPrompt
from models.my_model import MyModel


"""
长期记忆智能体：提取用户稳定的个人特征，存入向量库

通用化改造：不再局限于"面试者能力"，而是覆盖所有业务域中
长期有效的事实型信息（适合跨会话回忆），例如：
  - 专业、年级、技能、项目经历
  - 目标岗位、目标城市、求职偏好
  - 面试中暴露的薄弱点
"""


class LongAgent:
    def __init__(self, long_memory: LongMemory):
        self.model = MyModel.get_local_model()
        self.long_memory = long_memory
        self.prompt = BuilderPrompt.get_prompt("memory/long_agent.yaml")

    async def update(self, user_id, question: str):
        """更新长期记忆"""
        agent = create_agent(
            model=self.model,
            system_prompt=self.prompt,
            tools=[],
        )
        rs = await agent.ainvoke({"messages": [HumanMessage(content=question)]})
        content = rs["messages"][-1].content
        if content and content.strip():
            await self.long_memory.save(user_id, content)
