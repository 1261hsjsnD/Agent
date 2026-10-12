from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END
from langgraph.types import Command

from models.my_model import MyModel, INTERNAL_TAG
from agent.prompts.builder_prompt import BuilderPrompt
from agent.state.messages_state import MessagesState
from utils.json_utils import parse_json_block, to_int

"""
面试意图识别节点
从用户输入中识别：岗位（job）、科目（subjects）、题目数量（num）


"""
prompt = BuilderPrompt.get_prompt("interview/interview_intent_node.yaml")

DEFAULT_TOTAL = 5


def _to_num(value, default=DEFAULT_TOTAL) -> int:
    """把 LLM 返回的题目数量安全转成 int（1-50 范围外一律按默认值）"""
    return to_int(value, default=default, min_value=1, max_value=50)


async def interview_intent_node(state: MessagesState) -> Command | dict:
    print("[节点] interview_intent: 开始")
    user_input = state["messages"][-1].content

    # 是否处于"刚提示过可选岗位、等用户重新选岗位"的状态
    # 这个状态下如果识别不出岗位/科目，说明用户可能想聊别的 -> 退出面试域
    pending_job_select = state.get("interview_step") == "ask_job"

    model = MyModel.get_model()
    rs = await model.ainvoke([
        ("system", prompt),
        ("human", user_input),
    ], config={"tags": [INTERNAL_TAG]})   # 输出是 JSON，不让用户看到

    data = parse_json_block(rs.content)

    job = (data.get("job") or "").strip()
    subjects = data.get("subjects") or []
    num = _to_num(data.get("num"))
    print(f"[节点] interview_intent: job={job!r} subjects={subjects} "
          f"num={num} need_ask={data.get('need_ask')} pending={pending_job_select}")

    writer = get_stream_writer()

    # 识别出了岗位/科目 -> 正常继续面试流程（不需要输出，交由后续节点追问/出题）
    if job:
        # 用户说了岗位 -> 进入追问科目阶段（科目 + 题数会一起追问，由 manager 输出）
        return {
            "job_name": job,
            "total": num,
            "interview_step": "ask_subject",
        }

    if subjects:
        # 用户直接说了科目 -> 直接出题
        return {
            "subjects": subjects,
            "total": num,
            "interview_step": "intent_done",
        }

    # ---------- 以下都是"没识别出有效岗位/科目"的情况，需要向用户输出文本 ----------

    # 处于"等用户重新选岗位"状态 -> 说明用户可能不想面试了，退出面试域，
    if pending_job_select:
        reply = ("好的，那我们暂时先不面试了～你可以直接告诉我你想做什么，"
                 "比如「我要职业规划」「帮我查岗位」或者随便聊聊。")
        writer(reply)
        return Command(goto=END, update={
            "messages": [AIMessage(content=reply)],
            "interview_step": "",
            "job_name": "",
            "subjects": [],
            "current_domain": "",
        })

    # 首次进入没识别出 -> 追问
    if not data:
        reply = ("不好意思，我没听懂你想面试什么，能说清楚岗位或科目吗？"
                 "比如「我要面试后端开发」或「考我 javascript」。")
        writer(reply)
        return Command(goto=END, update={
            "messages": [AIMessage(content=reply)],
            "interview_step": "ask_subject",
        })

    if data.get("need_ask"):
        ask = data.get("ask") or "你想面试什么岗位或科目呢？"
        writer(ask)
        return Command(goto=END, update={
            "messages": [AIMessage(content=ask)],
            "interview_step": "ask_subject",
        })

    # 兜底追问
    reply = "你想面试什么岗位或科目呢？比如「后端开发」或「考我 python」。"
    writer(reply)
    return Command(goto=END, update={
        "messages": [AIMessage(content=reply)],
        "interview_step": "ask_subject",
    })
