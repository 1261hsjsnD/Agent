import json

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.config import get_stream_writer

from agent.state.messages_state import MessagesState
from agent.prompts.builder_prompt import BuilderPrompt
from db.career_db import query_jobs_by_major
from models.my_model import MyModel

"""
意向岗位推荐节点：
用户没有目标岗位时，用专业查 major_job_match 表拿到候选岗位方向，
让 LLM 流式生成推荐（打字机），并从文本中解析出岗位列表。
"""

prompt = BuilderPrompt.get_prompt("career/career_recommend_node.yaml")


def _parse_jobs(text: str) -> list:
    """从推荐文本中解析岗位名（格式：- 岗位名 | 理由）"""
    jobs = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("- ") and "|" in line:
            job = line[2:].split("|")[0].strip()
            if job and job not in jobs:
                jobs.append(job)
    return jobs


async def career_recommend_node(state: MessagesState) -> dict:
    profile = state.get("user_profile", {})
    major = profile.get("major", "")
    skills = profile.get("skills", [])

    # 1. 查库：按专业拿候选岗位方向
    recommend_jobs = await query_jobs_by_major(major)

    # 2. LLM 生成推荐
    model = MyModel.get_model()

    user_payload = json.dumps({
        "major": major,
        "skills": skills,
        "recommend_jobs": recommend_jobs,
    }, ensure_ascii=False)

    full_text = ""
    try:
        rs = await model.ainvoke([
            ("system", prompt),
            ("human", user_payload),
        ])
        full_text = rs.content
    except Exception:
        # 兜底：直接列出数据库岗位方向（走 custom 通道显示）
        if recommend_jobs:
            fallback = "、".join(recommend_jobs[:5])
            content = f"根据你的专业「{major}」，比较适合的方向有：{fallback}。你对哪个方向更感兴趣呢？"
        else:
            content = "暂时没有为你匹配到合适的岗位方向，能告诉我你更想往哪个方向发展吗？"
        get_stream_writer()(content)
        return {
            "career_step": "recommend",
            "recommend_jobs": recommend_jobs,
            "messages": [AIMessage(content=content)],
        }

    # 3. 从文本解析岗位列表
    parsed_jobs = _parse_jobs(full_text)

    return {
        "career_step": "recommend",
        "recommend_jobs": parsed_jobs or recommend_jobs,
        "messages": [AIMessage(content=full_text)],
    }
