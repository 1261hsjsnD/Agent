import json

from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END
from langgraph.types import Command

from agent.prompts.builder_prompt import BuilderPrompt
from agent.state.messages_state import MessagesState
from db.job_db import query_all_job_names,search_jobs,sort_by_salary,salary_overlap
from utils.json_utils import parse_json_block
from models.my_model import MyModel, INTERNAL_TAG


"""
找工作查询节点（终态）：
1. 把用户说的岗位方向映射到 job 表真实岗位名（LLM）
2. 按 岗位名 + 城市 查库
3. 按薪资区间过滤（Python 解析 salary 字符串）
4. LLM 组织成推荐报告，流式输出
"""
search_prompt =BuilderPrompt.get_prompt("job/job_search_node.yaml")
REPORT_PROMPT = BuilderPrompt.get_prompt("job/job_search_node_report.yaml")
async def map_job_names(direction: str, all_names: list) -> list:
    """把岗位方向映射到 job 表的真实岗位名（LLM 从给定列表里选）"""
    if not direction or not all_names:
        return []

    model = MyModel.get_model()
    names_text = "、".join(all_names)
    user_payload = f"岗位方向：{direction}\n数据库岗位名列表：{names_text}"

    rs = await model.ainvoke([
        ("system", search_prompt),
        ("human", user_payload),
    ], config={"tags": [INTERNAL_TAG]})   # 内部映射，不让用户看到

    data = parse_json_block(rs.content)
    mapped = data.get("jobs", [])

    # 代码层强校验：只保留确实存在于 job 表的岗位名
    name_set = set(all_names)
    return [m for m in mapped if isinstance(m, str) and m in name_set]


async def job_search_node(state: MessagesState) -> Command:
    direction = state.get("search_job", "")
    city = state.get("search_city", "")
    salary_min = state.get("search_salary_min", 0)
    salary_max = state.get("search_salary_max", 0)

    writer = get_stream_writer()
    model = MyModel.get_model()

    # 1. 映射岗位方向 -> job 表真实岗位名
    all_names = await query_all_job_names()
    job_names = await map_job_names(direction, all_names)

    if not job_names:
        content = (f"抱歉，暂时没有找到和「{direction}」相关的招聘岗位～\n"
                   f"你可以换个说法，比如具体的岗位名（Java、前端开发、测试工程师等）再试试。")
        writer(content)
        return Command(goto=END, update={
            "job_step": "done",
            "current_domain": "",
            "messages": [AIMessage(content=content)],
        })

    # 2. 按 岗位名 + 城市 查库
    rows = await search_jobs(job_names, city, limit=80)

    # 3. 按薪资区间过滤 + 排序
    if salary_min or salary_max:
        rows = [r for r in rows if salary_overlap(r.get("salary"), salary_min, salary_max)]
    rows = sort_by_salary(rows)

    if not rows:
        cond = f"「{direction}」"
        if city:
            cond += f" · {city}"
        content = f"抱歉，没有找到符合条件（{cond}）的招聘岗位，可以放宽城市或薪资条件再试试～"
        writer(content)
        return Command(goto=END, update={
            "job_step": "done",
            "current_domain": "",
            "messages": [AIMessage(content=content)],
        })

    # 4. LLM 组织推荐报告（token 由外层 messages 通道冒泡，节点内不 writer）
    limit_rows = rows[:15]
    user_payload = json.dumps({
        "岗位方向": direction,
        "城市": city or "不限",
        "薪资期望": f"{salary_min}-{salary_max}" if (salary_min or salary_max) else "不限",
        "命中岗位数": len(rows),
        "岗位数据": limit_rows,
    }, ensure_ascii=False)

    rs = await model.ainvoke([
        ("system", REPORT_PROMPT),
        ("human", user_payload),
    ])
    report = rs.content

    return Command(goto=END, update={
        "job_step": "done",
        "current_domain": "",
        "search_job_names": job_names,
        "messages": [AIMessage(content=report)],
    })
