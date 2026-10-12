from langgraph.graph import END
from langgraph.types import Command
from langgraph.config import get_stream_writer
from langchain_core.messages import HumanMessage, AIMessage

from agent.state.messages_state import MessagesState
from agent.prompts.builder_prompt import BuilderPrompt
from db.career_db import load_profile_from_db, save_target_job
from utils.json_utils import parse_json_block, to_bool
from models.my_model import MyModel, INTERNAL_TAG

"""
职业规划 manager 中枢节点

流程（画像已在个人信息页/简历上传时填好，这里不再追问收集）：
1. 读数据库画像（按 email）
2. 判断画像是否完整（major + skills + grade）
   - 不完整 -> 提示去完善信息，清空 domain，本轮结束
3. 检查 target_job：
   - 为空 -> 去 career_recommend 推荐岗位方向
   - 有值 -> 去 career_plan 出规划

状态机（career_step）：
    ""          首次进入，读画像判断
    "recommend"  已推荐岗位，等用户选择（本轮结束）
    "plan"       画像+岗位齐全，出规划
"""

#使用llm提取用户输入岗位返回岗位名称
async def extract_job_from_input(user_input: str, candidates: list) -> str:
    model = MyModel.get_model()
    jobs_text = "、".join(candidates) if candidates else "（本次没有候选列表，请按用户表述提取岗位名称）"
    system_prompt = BuilderPrompt.get_prompt("career/career_manager_node_extract.yaml").format(
        recommend_jobs=jobs_text
    )

    rs = await model.ainvoke([
        ("system", system_prompt),
        ("human", user_input),
    ], config={"tags": [INTERNAL_TAG]})  # 输出是 JSON，不让用户看到

    data = parse_json_block(rs.content, default=None)
    job = (data.get("job") or "").strip()
    if not job:
        return ""

    # LLM 没给 matched 时，用代码自己判断（matched 仅作参考，最终以代码校验为准）
    matched = to_bool(data.get("matched")) if "matched" in data else (job in candidates)

    # 代码层强校验：LLM 若返回列表外的说法但语义能对上，拉回规范岗位名
    if candidates and job not in candidates:
        for c in candidates:
            if c and (c in job or job in c):
                return c
        # 列表外且对不上任何候选 -> 保留 LLM 原话（走 judge 判断合理性）
        return job

    return job

async def career_manager_node(state: MessagesState) -> Command:
    email = state.get("user_email", "")
    step = state.get("career_step", "")

    # 判断最后一条消息是否为用户新输入
    last_msg = state["messages"][-1]
    is_user_input = isinstance(last_msg, HumanMessage)

    # 情况1：已推荐岗位，等用户选择 -> 提取用户输入的岗位名，写回，进规划
    if step == "recommend":
        if is_user_input:
            candidates = state.get("recommend_jobs", [])
            job = await extract_job_from_input(last_msg.content, candidates)
            if job:
                # 写入数据库画像，同时更新本轮 state 里的画像
                await save_target_job(email, job)
                profile = await load_profile_from_db(email)
                profile["target_job"] = job
                print(f"[规划] 用户选择岗位: {job}（候选: {candidates}）")
                return Command(goto="career_plan", update={
                    "user_profile": profile,
                    "career_step": "plan",
                })
        # 用户没输入有效岗位，继续等
        return Command(goto=END)

    # 情况2：首次进入或常规入口，读画像判断
    profile = await load_profile_from_db(email)

    # 2.1 画像不完整（只需 专业 + 年级）
    if not (profile.get("major") and profile.get("grade")):
        reply = "你的个人信息还不完整，请先到「个人信息」页面完善专业和年级，再来做职业规划哦～"
        writer = get_stream_writer()
        writer(reply)
        return Command(goto=END, update={
            "current_domain": "",
            "career_step": "",
            "messages": [AIMessage(content=reply)],
        })

    # 2.2 画像完整，检查 target_job
    if not profile.get("target_job"):
        # 没有目标岗位 -> 去推荐
        return Command(goto="career_recommend", update={"user_profile": profile})

    # 有目标岗位 -> 直接进规划
    return Command(goto="career_plan", update={
        "user_profile": profile,
        "career_step": "plan",
    })
