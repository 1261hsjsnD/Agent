from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import HumanMessage

from agent.state.messages_state import MessagesState

"""
找工作域 manager 中枢节点

job_step 状态机：
    ""            -> 首次进入，识别条件（岗位/城市/薪资）
    "ask_more"    -> 已追问（缺岗位），等用户补充
                     - 用户有输入 -> 再识别一次
                     - 用户没输入 -> 结束本轮，等用户输入
    "ready"       -> 条件齐全，去查询
    "done"        -> 查询完成，清空域
"""

async def job_manager_node(state: MessagesState) -> Command:
    step = state.get("job_step", "")
    last_msg = state["messages"][-1] if state.get("messages") else None
    is_user_input = isinstance(last_msg, HumanMessage)

    # 情况1：已追问缺岗位，等用户补充
    if step == "ask_more":
        if not is_user_input:
            # 上一轮刚追问完（最后一条是 AI），结束本轮等用户输入，避免空转
            return Command(goto=END)
        # 用户补充了信息 -> 再识别一次
        return Command(goto="job_intent")

    # 情况2：首次进入 -> 识别条件
    if step == "":
        return Command(goto="job_intent")

    # 情况3：条件齐全 -> 查询
    if step == "ready":
        return Command(goto="job_search")

    # 情况4：已完成 -> 清空域，结束
    if step == "done":
        return Command(goto=END, update={"current_domain": ""})

    # 兜底
    return Command(goto="job_intent")