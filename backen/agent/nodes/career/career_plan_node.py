import json
from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END
from langgraph.types import Command
from agent.state.messages_state import MessagesState
from db.career_db import query_jobs_by_major, query_job_profile, query_job_raw
from utils.json_utils import parse_json_block
from agent.prompts.builder_prompt import BuilderPrompt
from models.my_model import MyModel, INTERNAL_TAG

"""
职业规划核心节点：

1. 查 job_profile 表：目标岗位有没有岗位画像
   - 有画像 -> 精准规划（结合岗位要求 + 用户画像给建议）
2. 画像没有，但岗位属于该专业的推荐方向（major_job_match）-> 用 job 表原始信息 + 通用建议
3. 既没画像、也不在推荐方向 -> 让大模型判断这个岗位是否合理
   - 合理 -> 给通用建议
   - 不合理 -> 提醒用户没这个岗位
"""
prompt = BuilderPrompt.get_prompt("career/career_plan.yaml")

# 判断岗位是否合理/真实的提示词
judge_prompt = BuilderPrompt.get_prompt("career/career_planning_judge_node.yaml")


def _decide_route(grade: str, has_project: bool) -> str:
    """代码判断规划路线（确定性规则，不交给 LLM）"""
    if grade in ("大一", "大二"):
        return "internship"                     # 实习路线
    if grade in ("大三", "大四", "研二", "研三"):
        # 高年级：有项目走求职，无项目先补项目经验
        return "job" if has_project else "job_prepare"
    return "general"                            # 其他通用提升


async def _judge_job(job_name: str) -> dict:
    """让大模型判断岗位是否合理

    打上 INTERNAL_TAG：这是逻辑判断，输出是 JSON，不能让它流到前端。

    """
    model = MyModel.get_model()
    rs = await model.ainvoke([
        ("system", judge_prompt),
        ("human", job_name),
    ], config={"tags": [INTERNAL_TAG]})
    return parse_json_block(rs.content, default={"is_valid": True, "reason": ""})


async def _stream_plan(profile: dict, target_job: str, grade: str, route: str,
                       job_profile: dict, job_raw: list) -> str:
    model = MyModel.get_model()

    user_payload = json.dumps({
        "profile": profile,
        "target_job": target_job,
        "grade": grade,
        "route": route,
        "project_experience": profile.get("project_experience", ""),
        "job_profile": job_profile,
        "job_raw": job_raw,
    }, ensure_ascii=False)

    rs = await model.ainvoke([
        ("system", prompt),
        ("human", user_payload),
    ])
    return rs.content


async def career_plan_node(state: MessagesState) -> Command:
    profile = state.get("user_profile", {})
    target_job = profile.get("target_job", "")
    major = profile.get("major", "")
    grade = profile.get("grade", "")

    # 1. 查岗位画像
    job_profile = await query_job_profile(target_job)

    # 2. 查该专业推荐方向（判断岗位是否属于专业对口）
    match_jobs = await query_jobs_by_major(major)
    in_match = target_job in match_jobs

    # 3. 判断路线
    has_project = bool(profile.get("project_experience"))
    route = _decide_route(grade, has_project)

    # 4. 三层分支（规划是终态，出完直接 END，不回 manager）
    if job_profile:
        # 第一层：有岗位画像 -> 精准规划
        content = await _stream_plan(profile, target_job, grade, route, job_profile, [])
        return Command(goto=END, update={
            "career_step": "done",
            "current_domain": "",
            "messages": [AIMessage(content=content)],
        })

    if in_match:
        # 第二层：属于专业对口但没画像 -> 用 job 表原始信息 + 通用建议
        job_raw = await query_job_raw(target_job)
        content = await _stream_plan(profile, target_job, grade, route, {}, job_raw)
        return Command(goto=END, update={
            "career_step": "done",
            "current_domain": "",
            "messages": [AIMessage(content=content)],
        })

    # 第三层：既没画像也不对口 -> 大模型判断
    judge = await _judge_job(target_job)
    if judge.get("is_valid"):
        content = await _stream_plan(profile, target_job, grade, route, {}, [])
        return Command(goto=END, update={
            "career_step": "done",
            "current_domain": "",
            "messages": [AIMessage(content=content)],
        })

    # 大模型判断岗位不存在/不合理 -> 提醒用户（走 custom 通道显示）
    content = f"抱歉，没有找到「{target_job}」这个岗位的相关信息。你确定岗位名称正确吗？可以换个说法再试试～"
    get_stream_writer()(content)
    return Command(goto=END, update={
        "career_step": "",
        "current_domain": "",
        "messages": [AIMessage(content=content)],
    })
