from langgraph.graph import END
from langgraph.types import Command
from langgraph.config import get_stream_writer
from langchain_core.messages import HumanMessage, AIMessage

from agent.prompts.builder_prompt import BuilderPrompt
from agent.state.messages_state import MessagesState
from db.interview_db import query_job_subjects, query_all_jobs
from utils.json_utils import parse_json_block, to_int
from models.my_model import MyModel, INTERNAL_TAG

"""
面试 manager 中枢节点

interview_step 状态机：
    ""            -> 识别岗位/科目/题数
    "ask_subject" -> 已识别岗位，追问选科目（等用户选）；或用户直接说科目则进 intent_done
    "intent_done" -> 科目已确定，开始出题
    "question"    -> 已出题，等待用户答题
    "answered"    -> 已记录答案，判断继续出题 or 评价
    "done"        -> 评价完成
"""

# 追问科目的固定标记：用于判断"是否已经追问过"，避免首次进入就把用户原话当科目
ASK_SUBJECT_FLAG = "你想考哪个"

# 从用户输入提取科目 + 题目数量的提示词
SUBJECT_PROMPT = BuilderPrompt.get_prompt("interview/interview_manager_node.yaml")

DEFAULT_TOTAL = 5


def _to_num(value) -> int:
    """把 LLM 返回的数量安全转成 int（非法/未提供返回 0，范围外返回 0）"""
    return to_int(value, default=0, min_value=1, max_value=50)


async def  extract_subjects_and_num(user_input: str, valid_subjects: list) -> tuple:
    """用 LLM 从用户输入中提取「科目」和「题目数量」

    返回 (subjects, num)：
      - subjects：只保留 valid_subjects 中真实存在的科目
      - num：用户明确说出的题数；没说则返回 0（调用方沿用旧值或默认值）

    加「候选科目约束 + 代码层强校验」，防止 LLM 把用户说的岗位名
    （如"前端开发"）当成科目，导致后续查不到题、直接空跑进评价环节。
    """
    if not valid_subjects:
        return [], 0

    model = MyModel.get_model()
    valid_text = "、".join(valid_subjects)
    prompt = SUBJECT_PROMPT.format(valid_subjects=valid_text)

    rs = await model.ainvoke([
        ("system", prompt),
        ("human", user_input),
    ], config={"tags": [INTERNAL_TAG]})   # 输出是 JSON，不让用户看到

    data = parse_json_block(rs.content)

    # 代码层强校验：只保留真实存在于该岗位科目列表里的（大小写不敏感）
    picked = data.get("subjects", [])
    result = []
    if isinstance(picked, list):
        valid_map = {s.strip().lower(): s.strip() for s in valid_subjects}
        for s in picked:
            if not isinstance(s, str):
                continue
            key = s.strip().lower()
            if key in valid_map and valid_map[key] not in result:
                result.append(valid_map[key])

    num = _to_num(data.get("num"))
    return result, num


async def interview_manager_node(state: MessagesState) -> Command:
    step = state.get("interview_step", "")
    last_msg = state["messages"][-1] if state.get("messages") else None
    is_user_input = isinstance(last_msg, HumanMessage)
    print(f"[节点] interview_manager: step={step!r} is_user_input={is_user_input}")

    # 情况1：已识别岗位，等用户选科目
    if step == "ask_subject":
        job_name = state.get("job_name", "")

        # 该岗位真实可选的科目（后面提取 / 追问都要用）
        job_subjects = await query_job_subjects(job_name) if job_name else []

        # 是否"已经追问过科目"：最近几条 AI 消息里出现过追问标记。
        # 少了这个判断，首次进入时 last_msg 仍是用户那句"我要面试前端开发"，
        # 会被当成"用户在选科目"去提取 -> 把岗位名当科目 -> 查不到题直接空跑进评价。
        asked = any(
            isinstance(m, AIMessage) and ASK_SUBJECT_FLAG in (m.content or "")
            for m in state["messages"][-4:]
        )

        # 用户有输入，且确实追问过 -> 才去提取科目（顺带提取题目数量）
        if is_user_input and job_name and asked:
            subjects, num = await extract_subjects_and_num(last_msg.content, job_subjects)
            print(f"[节点] interview_manager: 提取科目={subjects} 题数={num}")
            if subjects:
                # 用户选了科目 -> 进入出题（题数：用户说了用用户的，没说沿用旧值/默认 5）
                old_total = state.get("total") or DEFAULT_TOTAL
                return Command(goto="interview_question", update={
                    "subjects": subjects,
                    "total": num or old_total,
                    "interview_step": "intent_done",
                })

        # 还没追问过（或用户没选出有效科目）-> 查岗位的科目列表并追问
        if job_name:
            writer = get_stream_writer()
            if job_subjects:
                subjects_str = "、".join(job_subjects)
                old_total = state.get("total") or DEFAULT_TOTAL
                reply = (f"「{job_name}」包含这些科目：{subjects_str}。{ASK_SUBJECT_FLAG}？"
                         f"可以选一个，也可以选两个混合出题～\n"
                         f"想练几道题？（不说的话默认 {old_total} 道）")
                print(f"[节点] interview_manager: 追问科目 -> {subjects_str}")
                writer(reply)
                return Command(goto=END, update={
                    "messages": [AIMessage(content=reply)],
                })
            else:
                # 岗位不在题库 -> 告知用户目前题库收录了哪些岗位，
                # 并进入 ask_job 状态等用户重新选岗位。
                # 注意：这里【保留 current_domain="interview"】，用户下一句
                # 直接说岗位名（如"前端开发"）时会继续留在面试域里被正确识别，
                # 而不是被清空域后重新走意图识别（曾导致"前端开发"被识别成闲聊）。
                all_jobs = await query_all_jobs()
                if all_jobs:
                    jobs_str = "、".join(all_jobs)
                    reply = (f"抱歉，暂时还没有「{job_name}」相关的面试题～\n"
                             f"当前题库收录的岗位有：{jobs_str}。\n"
                             f"你可以从这些岗位里选一个来练习哦～")
                else:
                    reply = f"抱歉，暂时没有「{job_name}」相关的题库，你可以换个岗位试试～"
                writer(reply)
                return Command(goto=END, update={
                    "messages": [AIMessage(content=reply)],
                    "job_name": "",                  # 清掉无效岗位
                    "interview_step": "ask_job",     # 等用户重新选岗位
                    # current_domain 保持 "interview"
                })

        # 没有 job_name：
        # - 最后一条是 AI 消息，说明上面已经追问过了 -> 结束本轮等用户输入，
        #   否则会不停在 manager 和 interview_intent 之间打转（死循环）
        # - 最后一条是用户消息 -> 再识别一次，可能是用户直接说了科目
        if not is_user_input:
            return Command(goto=END)
        return Command(goto="interview_intent")

    # 情况0：刚提示过"当前收录的岗位"，等用户重新选岗位
    #   - 最后一条是 AI 消息 -> 提示刚发出，结束本轮等用户输入
    #   - 用户有输入 -> 交给 interview_intent 识别新岗位
    #     （识别不出有效岗位时，intent 会清空 current_domain 退出面试域，
    #       避免用户被"困"在面试流程里出不去）
    if step == "ask_job":
        if not is_user_input:
            return Command(goto=END)
        return Command(goto="interview_intent", update={"interview_step": "ask_job"})

    # 情况2：首次进入
    if step == "":
        return Command(goto="interview_intent")

    # 情况3：科目已确定，开始出题
    if step == "intent_done":
        return Command(goto="interview_question")

    # 情况4：已出题，等答题
    if step == "question":
        # 最后一条不是用户消息 = 还没收到答案，本轮到此结束等用户输入。
        # 少了这个判断就会 manager -> answer -> manager -> answer 空转，
        # 直到撞上 recursion_limit。
        if not is_user_input:
            return Command(goto=END)
        return Command(goto="interview_answer")

    # 情况5：已记录答案，判断继续还是评价
    if step == "answered":
        if state.get("continue_question"):
            return Command(goto="interview_question")
        return Command(goto="interview_evaluate")

    # 情况6：评价完成
    if step == "done":
        return Command(goto=END, update={"current_domain": ""})

    # 兜底
    return Command(goto="interview_intent")
