from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END
from langgraph.types import Command

from agent.state.messages_state import MessagesState
from db.interview_db import query_questions, query_job_subjects

"""
出题节点：按科目随机抽一道未出过的题（支持单/双科目混合）
"""


async def interview_question_node(state: MessagesState) -> Command | dict:
    subjects = state.get("subjects", [])
    num = state.get("total", 5)
    question_list = state.get("questions") or []
    current = state.get("current_id", 0) + 1

    # 已出过的题目 id，避免重复
    exclude_ids = [q["id"] for q in question_list if q.get("id")]

    # 查一道题（多科目随机混合）
    rows = await query_questions(subjects, exclude_ids, limit=1)

    writer = get_stream_writer()

    if not rows:
        # 区分两种情况，避免"一道题都没出过"还硬进评价环节
        if question_list:
            # 已经出过题 -> 确实出完了，正常进入评价
            writer("题目已经出完啦～")
            return {
                "messages": [AIMessage(content="题目已经出完啦～")],
                "interview_step": "answered",
                "continue_question": False,
            }

        # 一道题都没出过 -> 科目/题库配置有问题，不能进评价
        # 顺便把该岗位当前可选的科目告诉用户，方便重新选择
        job_name = state.get("job_name", "")
        job_subjects = await query_job_subjects(job_name) if job_name else []
        if job_subjects:
            subjects_str = "、".join(job_subjects)
            reply = (f"抱歉，暂时没有找到对应的面试题～\n"
                     f"「{job_name}」目前可选的科目有：{subjects_str}，你可以重新选一个～")
        else:
            reply = "抱歉，暂时没有找到这个科目的面试题，请换个科目或者重新开始一次面试～"
        writer(reply)
        return Command(goto=END, update={
            "messages": [AIMessage(content=reply)],
            "current_domain": "",
            "interview_step": "",
            "subjects": [],
        })

    # rows[0] = {"id":..., "subject":..., "question":..., "answer":...}
    row = rows[0]
    qid = row["id"]
    qsubject = row["subject"]
    qquestion = row["question"]
    qanswer = row["answer"]

    question_list.append({
        "id": qid,
        "subject": qsubject,
        "question": qquestion,
        "answer": qanswer,
    })

    ai_msg = f"\n第{current}题（{qsubject}）：{qquestion}\n"

    writer(ai_msg)
    return {
        "messages": [AIMessage(content=ai_msg)],
        "questions": question_list,
        "total": num,
        "current_id": current,
        "question_id": qid,
        "interview_step": "question",
    }
