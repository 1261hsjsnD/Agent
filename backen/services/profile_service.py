import json

from pydantic import BaseModel
from typing import List

from db.dao.postgres import get_pool


class StudentModel(BaseModel):
    """学生信息表单模型（对应前端 student 对象）"""
    name: str = ""
    gender: str = ""
    phone: str = ""
    email: str = ""
    school: str = ""
    major: str = ""
    education: str = ""
    grade: str = ""
    target_city: str = ""
    target_job: str = ""
    skills: List[str] = []
    certificates: List[str] = []
    pressure_ability: str = ""
    internship: List[str] = []
    project_experience: List[str] = []
    campus_experience: List[str] = []


def _json_to_list(value) -> list:
    """把 jsonb 字段值安全转成 list（

    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
        except (json.JSONDecodeError, TypeError):
            # 不是合法 JSON（例如纯文本项目描述）-> 当成单条内容
            return [s]
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, str):
            # 双重编码 / 历史脏数据：解析出来仍是字符串
            return [parsed] if parsed.strip() else []
        return [str(parsed)]
    return []


async def upsert_profile(student: StudentModel) -> dict:
    """把学生信息 upsert 到 student 表（jsonb 字段转 JSON 字符串存储）"""
    pool = get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO student
                        (name, gender, phone, email, school, major, education, grade,
                         target_city, target_job, skills, certificates, pressure_ability,
                         internship, project_experience, campus_experience)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (email)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        gender = EXCLUDED.gender,
                        phone = EXCLUDED.phone,
                        school = EXCLUDED.school,
                        major = EXCLUDED.major,
                        education = EXCLUDED.education,
                        grade = EXCLUDED.grade,
                        target_city = EXCLUDED.target_city,
                        target_job = EXCLUDED.target_job,
                        skills = EXCLUDED.skills,
                        certificates = EXCLUDED.certificates,
                        pressure_ability = EXCLUDED.pressure_ability,
                        internship = EXCLUDED.internship,
                        project_experience = EXCLUDED.project_experience,
                        campus_experience = EXCLUDED.campus_experience
                    """,
                    (
                        student.name,
                        student.gender,
                        student.phone,
                        student.email,
                        student.school,
                        student.major,
                        student.education,
                        student.grade,
                        student.target_city,
                        student.target_job,
                        json.dumps(student.skills, ensure_ascii=False),
                        json.dumps(student.certificates, ensure_ascii=False),
                        student.pressure_ability,
                        json.dumps(student.internship, ensure_ascii=False),
                        json.dumps(student.project_experience, ensure_ascii=False),
                        json.dumps(student.campus_experience, ensure_ascii=False),
                    ),
                )
        return {"code": 200, "msg": "用户信息保存成功"}
    except Exception as e:
        return {"code": 400, "msg": f"用户信息保存失败: {e}"}


async def query_profile(email: str) -> dict:
    """按 email 查询学生信息，返回完整画像（jsonb 字段转回 list）"""
    if not email:
        return {"code": 400, "msg": "email 不能为空", "data": None}

    pool = get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT name, gender, phone, email, school, major, education, grade,
                           target_city, target_job, skills, certificates, pressure_ability,
                           internship, project_experience, campus_experience, interview_ability
                    FROM student
                    WHERE email = %s
                """, (email,))
                row = await cur.fetchone()
    except Exception as e:
        return {"code": 400, "msg": f"查询失败: {e}", "data": None}

    if not row:
        return {"code": 200, "msg": "未找到用户信息", "data": None}

    data = {
        "name": row[0] or "",
        "gender": row[1] or "",
        "phone": row[2] or "",
        "email": row[3] or "",
        "school": row[4] or "",
        "major": row[5] or "",
        "education": row[6] or "",
        "grade": row[7] or "",
        "target_city": row[8] or "",
        "target_job": row[9] or "",
        "skills": _json_to_list(row[10]),
        "certificates": _json_to_list(row[11]),
        "pressure_ability": row[12] or "",
        "internship": _json_to_list(row[13]),
        "project_experience": _json_to_list(row[14]),
        "campus_experience": _json_to_list(row[15]),
        "interview_ability": row[16] or "",
    }
    return {"code": 200, "msg": "查询成功", "data": data}


async def save_resume_to_student(email: str, profile: dict) -> dict:
    """把简历解析结果 upsert 到 student 表（只更新简历能解析出的字段）"""
    if not email:
        return {"code": 400, "msg": "email 不能为空"}

    # 简历的 skills 是 List[Skill]（含 name/level），抽 name；certificates 同理
    skills = [s.get("name", "") for s in profile.get("skills", []) if s.get("name")]
    certificates = [c.get("name", "") for c in profile.get("certificates", []) if c.get("name")]

    # 项目经验：简历解析出的是「一整段文字」，统一包成单元素列表，
    # 与 student.project_experience(jsonb 数组) 的存储协议保持一致
    proj = (profile.get("project_experience") or "").strip()
    project_list = [proj] if proj else []

    # 实习经历：简历解析出的是对象列表（company/role/duration/description），
    # 压成字符串列表，前端 joinFromArray 才能正常显示（否则会变成 [object Object]）
    internships = []
    for i in profile.get("internships", []):
        company = (i.get("company") or "").strip()
        role = (i.get("role") or "").strip()
        duration = (i.get("duration") or "").strip()
        desc = (i.get("description") or "").strip()
        text = " ".join(x for x in [company, role, duration] if x)
        if desc:
            text = f"{text}：{desc}" if text else desc
        if text:
            internships.append(text)

    pool = get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO student (email, name, school, major, education,
                                         skills, certificates, pressure_ability,
                                         internship, project_experience)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (email)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        school = EXCLUDED.school,
                        major = EXCLUDED.major,
                        education = EXCLUDED.education,
                        skills = EXCLUDED.skills,
                        certificates = EXCLUDED.certificates,
                        pressure_ability = EXCLUDED.pressure_ability,
                        internship = EXCLUDED.internship,
                        project_experience = EXCLUDED.project_experience
                    """,
                    (
                        email,
                        profile.get("name", ""),
                        profile.get("school", ""),
                        profile.get("major", ""),
                        profile.get("education", ""),
                        json.dumps(skills, ensure_ascii=False),
                        json.dumps(certificates, ensure_ascii=False),
                        profile.get("pressure_ability", ""),
                        json.dumps(internships, ensure_ascii=False),
                        json.dumps(project_list, ensure_ascii=False),
                    ),
                )
        return {"code": 200, "msg": "简历信息保存成功"}
    except Exception as e:
        return {"code": 400, "msg": f"简历信息保存失败: {e}"}
