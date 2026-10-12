
from langgraph.types import Command

from agent.state.messages_state import MessagesState

"""
入口管理检查是否有进行的状态对应跳转，否则意图识别
"""
async def main_manager_node(state:MessagesState):
    domain = state.get("current_domain", "")
    print(f"[节点] main_manager: domain={domain}")

    if domain == "career_planning":
        return Command(goto="career_manager")

    if domain == "interview":
        return Command(goto="interview_manager")

    if domain == "job_search":
        return Command(goto="job_manager")

    # 空闲：先识别意图
    return Command(goto="intent")