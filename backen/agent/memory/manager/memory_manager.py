import asyncio

from agent.memory.retrieval.long_agent import LongAgent
from agent.memory.retrieval.summary_agent import SummaryAgent
import os
from dotenv import load_dotenv
load_dotenv()
"""
记忆管理器：每轮对话后更新各层记忆

职责划分：
  - 窗口记忆：由 graph.py 每轮直接读写（本类不负责）
  - 摘要记忆：本类负责，每积累够 SUMMARY_INTERVAL 条才更新一次
  - 长期记忆：本类负责，每积累够 LONG_INTERVAL 条才提取一次（只喂新增那批）
  - 画像记忆：
      面试能力画像由面试流程（interview_evaluate_node）负责，
   

"""

# 每积累多少条新消息触发一次长期记忆提取
LONG_INTERVAL = 6


def _format_messages(messages: list) -> str:
    """把窗口消息拼成「用户提问 / AI回复」的文本"""
    text = ""
    for i in messages:
        if i["role"] == "user":
            text += f"用户提问：{i['content']}\n"
        else:
            text += f"AI回复：{i['content']}\n"
    return text


class MemoryManager:
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.summary_agent = SummaryAgent(session_manager.summary_memory)
        self.window_memory = session_manager.window_memory
        self.long_agent = LongAgent(session_manager.long_memory)

    async def update(self, user_id: str):
        """更新长期记忆 + 摘要记忆（画像记忆不在此更新）"""
        # 获取窗口记忆（最近 N 条原文）
        query_window = await self.window_memory.query()

        # 累计消息总数 用于按增量触发
        total_count = await self.window_memory.total_count()

        # 1. 长期记忆：每积累 LONG_INTERVAL(6) 条新消息提取一次，

        if total_count > 0 and total_count % LONG_INTERVAL == 0:
            batch = query_window[-LONG_INTERVAL:] if len(query_window) >= LONG_INTERVAL else query_window
            tasks = [self.long_agent.update(user_id, _format_messages(batch))]
        else:
            tasks = []

        # 2. 摘要记忆：按「累计消息总数」每满 SUMMARY_INTERVAL 条触发一次

        if SummaryAgent.should_update(total_count):
            tasks.append(self.summary_agent.update(query_window))

        # 并行执行，缩短总耗时
        if tasks:
            await asyncio.gather(*tasks)
