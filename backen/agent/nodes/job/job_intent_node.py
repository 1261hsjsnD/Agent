from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer

from agent.prompts.builder_prompt import BuilderPrompt
from agent.state.messages_state import MessagesState



from models.my_model import MyModel, INTERNAL_TAG
from utils.json_utils import to_int, parse_json_block

"""
找工作意图识别节点：
从用户输入中提取 岗位（必填）、城市（可空）、期望薪资（可空）
信息不全时生成一次性追问（问全三个条件）。

注意：输出是 JSON，属于内部判断，打 INTERNAL_TAG 防止漏到前端。
"""

prompt = BuilderPrompt.get_prompt("job/job_intent_node.yaml")

# 一次性追问话术（LLM 未生成 ask 时兜底）
ASK_ALL = "你想找什么岗位？在哪个城市？期望薪资多少？（城市和薪资可以不说，也可以一起告诉我）"


def to_salary(value) -> int:
    """把 LLM 返回的薪资值安全转成 int（兼容 "15000" / 15000 / "1.5万"，非法返回 0）"""
    return to_int(value, default=0, min_value=0)


async def job_intent_node(state: MessagesState) -> dict :
    user_input = state["messages"][-1].content

    # 已经提取过的条件（多轮补充时，新信息覆盖旧信息，没提到则沿用旧的）
    old_job = state.get("search_job", "")
    old_city = state.get("search_city", "")
    old_min = state.get("search_salary_min", 0)
    old_max = state.get("search_salary_max", 0)

    model = MyModel.get_model()
    rs = await model.ainvoke([
        ("system", prompt),
        ("human", user_input),
    ], config={"tags": [INTERNAL_TAG]})   # 输出是 JSON，不让用户看到

    data = parse_json_block(rs.content)

    # 新信息优先，没提到则沿用上一轮
    job = (data.get("job") or "").strip() or old_job
    city = (data.get("city") or "").strip() or old_city
    salary_min = to_salary(data.get("salary_min")) or old_min
    salary_max = to_salary(data.get("salary_max")) or old_max

    # 岗位是必填：没有岗位就追问（一次性问全）
    if not job:
        ask = (data.get("ask") or "").strip() or ASK_ALL
        # 本节点不在流式白名单，追问属于固定文本，走 custom 通道显示
        get_stream_writer()(ask)
        return {
            "job_step": "ask_more",
            "search_job": "",
            "search_city": city,
            "search_salary_min": salary_min,
            "search_salary_max": salary_max,
            "messages": [AIMessage(content=ask)],
        }

    # 岗位有了 -> 条件齐全，准备查询
    return {
        "job_step": "ready",
        "search_job": job,
        "search_city": city,
        "search_salary_min": salary_min,
        "search_salary_max": salary_max,
    }
