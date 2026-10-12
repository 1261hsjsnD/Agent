from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from agent.memory.save.summary_memory import SummaryMemory
from agent.prompts.builder_prompt import BuilderPrompt
from models.my_model import MyModel
import os
from dotenv import load_dotenv
load_dotenv()

"""
摘要智能体：根据旧摘要和最新问答生成新摘要

通用化改造：不再局限于"面试"场景，而是覆盖职业规划 / 模拟面试 / 找工作 / 闲聊
所有业务域，只保留「客观事实」和「关键结论」，去掉寒暄与重复。
"""




class SummaryAgent:
    def __init__(self, summary_memory: SummaryMemory):
        self.model = MyModel.get_local_model()
        self.summary_memory = summary_memory
        self.prompt = BuilderPrompt.get_prompt("memory/summary_agent.yaml")

    @staticmethod
    def should_update(total_count: int) -> bool:
        """是否该更新摘要：累计消息数每满 SUMMARY_INTERVAL 条触发一次

        """
        if not total_count or total_count <= 0:
            return False
        return total_count % int(os.getenv("SUMMARY_INTERVAL")) == 0

    async def update(self, messages: list):
        """根据窗口记忆更新摘要"""
        # 查询旧摘要
        old_summary = await self.summary_memory.query()

        # 最新聊天记录
        prompt = ""
        for i in messages:
            if i["role"] == "user":
                prompt += f"用户提问：{i['content']}\n"
            else:
                prompt += f"AI回复：{i['content']}\n"

        question = f"旧摘要:{old_summary}\n最新聊天记录:{prompt}"

        agent = create_agent(
            model=self.model,
            system_prompt=self.prompt,
            tools=[],
        )
        rs = await agent.ainvoke({"messages": [HumanMessage(content=question)]})
        new_summary = rs["messages"][-1].content

        # 存新摘要
        await self.summary_memory.save(new_summary)
