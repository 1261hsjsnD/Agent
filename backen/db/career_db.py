import json
from db.dao.postgres import get_pool
from utils.json_utils import json_to_list
#按照eamil加载画像
async def load_profile_from_db(email: str) -> dict:
    profile = {}
    if not email:
        return profile
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT major, skills, grade, target_job, project_experience,
                       school, education, target_city
                FROM student WHERE email = %s
                """,
                (email,),
            )
            row = await cur.fetchone()
    if not row:
        return profile
    profile["major"] = row[0] or ""
    profile["skills"] = json_to_list(row[1])
    profile["grade"] = row[2] or ""
    profile["target_job"] = row[3] or ""
    profile["project_experience"] = json_to_list(row[4])
    profile["school"] = row[5] or ""
    profile["education"] = row[6] or ""
    profile["target_city"] = row[7] or ""
    return profile
#按专业查 major_job_match 表，返回候选岗位方向列表
async def query_jobs_by_major(major: str) -> list:
    """按专业查 major_job_match 表，返回候选岗位方向列表"""
    if not major:
        return []

    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT job_direction FROM major_job_match
                WHERE majors = %s OR majors LIKE %s
                """,
                (major, f"%{major}%"),
            )
            rows = await cur.fetchall()

    jobs = []
    for row in rows:
        direction = row[0]
        if not direction:
            continue
        for j in direction.split(","):
            j = j.strip()
            if j and j not in jobs:
                jobs.append(j)
    return jobs

#查岗位画像（job_profile 表），返回 dict 或空 dict
async def query_job_profile(job_name: str) -> dict:

    if not job_name:
        return {}

    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT skills, certificates, project_experience,
                       pressure_ability, communication, learning_ability, internship
                FROM job_profile WHERE job_name = %s
                """,
                (job_name,),
            )
            row = await cur.fetchone()

    if not row:
        return {}
    return {
        "skills": row[0],
        "certificates": row[1],
        "project_experience": row[2],
        "pressure_ability": row[3],
        "communication": row[4],
        "learning_ability": row[5],
        "internship": row[6],
    }
#查 job 表原始岗位信息（兜底用），返回岗位列表
async def query_job_raw(job_name: str) -> list:
    """查 job 表原始岗位信息（兜底用），返回岗位列表"""
    if not job_name:
        return []

    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT job_name, city, district, salary, company_name
                FROM job WHERE job_name LIKE %s
                LIMIT 10
                """,
                (f"%{job_name}%",),
            )
            rows = await cur.fetchall()

    result = []
    for r in rows:
        item = {
            "job_name": r[0],
            "city": r[1],
            "district": r[2],
            "salary": r[3],
            "company_name": r[4],
        }
        result.append(item)
    return result
#把用户确认的目标岗位写入student表
async def save_target_job(email: str, target_job: str) -> None:
    """把用户确认的目标岗位写回 student 表"""
    if not email or not target_job:
        return

    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE student SET target_job = %s WHERE email = %s",
                (target_job, email),
            )
