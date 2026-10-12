from db.dao.mysql import query
from db.dao.postgres import get_pool
"""
面试题库抽取，面试能力提取
"""
async def query_job_subjects(job_name:str)->list:
    if not job_name:
        return []
    rows = await query(
        "SELECT subjects FROM job_category WHERE job_name = %s",
        (job_name,),
    )
    if not rows:
        return []
    subjects = rows[0]["subjects"]
    if not subjects:
        return []
    return [s.strip() for s in subjects.split(",") if s.strip()]
# 获取面试题
async def query_questions(subjects: list, exclude_ids: list = None, limit: int = 1) -> list:
    if not subjects:
        return []


    placeholders = ",".join(["%s"] * len(subjects))
    sql = (f"SELECT id, subject, question, answer FROM question_bank "
           f"WHERE subject IN ({placeholders})")
    params = list(subjects)

    if exclude_ids:
        id_ph = ",".join(["%s"] * len(exclude_ids))
        sql += f" AND id NOT IN ({id_ph})"
        params.extend(exclude_ids)

    sql += " ORDER BY RAND() LIMIT %s"
    params.append(limit)

    rows = await query(sql, tuple(params))
    return [
        {"id": r["id"], "subject": r["subject"],
         "question": r["question"], "answer": r["answer"]}
        for r in rows
    ]


# 获取所有岗位题库
async def query_all_jobs() -> list:
    rows = await query("SELECT job_name FROM job_category ORDER BY job_name")
    return [r["job_name"] for r in rows if r["job_name"]]
#检查科目是否在题库中有题目
async def check_subject_exists(subject: str) -> bool:

    rows = await query(
        "SELECT id FROM question_bank WHERE subject = %s LIMIT 1",
        (subject,),
    )
    return len(rows) > 0

#把面试能力画像写回 student 表
async def update_interview_ability(email: str, ability_text: str) -> None:
    """把面试能力画像写回 student 表"""
    if not email or not ability_text:
        return

    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE student SET interview_ability = %s WHERE email = %s",
                (ability_text, email),
            )
