from langchain_core.messages import HumanMessage, AIMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END
from langgraph.types import Command

from agent.state.messages_state import MessagesState

"""
答题节点：收集用户答案，判断下一个节点是去评价还是继续出题

关键：本节点通过 add_edge 回连 interview_manager，所以「等用户回答」时必须
用 Command(goto=END) 主动结束本轮。否则最后一条消息是 AIMessage 时
step 不变，manager 会把它再派回本节点 -> 无限空转直到 recursion_limit。
"""


async def interview_answer_node(state: MessagesState) -> dict:
    last_msg = state["messages"][-1]
    writer = get_stream_writer()

    if isinstance(last_msg, HumanMessage):
        user_input = last_msg.content
        question_id = state.get("question_id", 0)
        user_answer_list = state.get("user_answer_list") or []
        user_answer_list.append({"id": question_id, "answer": user_input})

        total = state.get("total", 5)
        if len(user_answer_list) < total:
            continue_question = True
        else:
            continue_question = False

        reply = "\n答案已经记录\n"
        writer(reply)
        return {
            "messages": [AIMessage(content=reply)],
            "user_answer_list": user_answer_list,
            "continue_question": continue_question,
            "interview_step": "answered",
        }
    else:
        # 还没收到用户答案：本轮到此结束，等用户下一轮输入。
        # 必须显式 goto=END，否则回 manager 后会被再次派回本节点（死循环）。
        reply = "\n请回答当前题目\n"
        writer(reply)
        return Command(
            goto=END,
            update={"messages": [AIMessage(content=reply)]},
        )
