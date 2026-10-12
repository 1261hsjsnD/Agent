from fastapi import APIRouter, UploadFile, File, Query
from pathlib import Path

from services.resume_service import list_templates, analysis_resume, save_resume_to_student

resume_router = APIRouter()


@resume_router.get("/templates")
async def get_templates():
    data = list_templates()
    return {"code": 200, "msg": "查询成功", "data": data}


@resume_router.post("/upload")
async def upload_resume(file: UploadFile = File(...), email: str = Query("")):
    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".docx"}:
        return {"code": 400, "msg": "只支持 PDF/Word(.docx)", "data": None}

    if not email:
        return {"code": 400, "msg": "缺少 email 参数", "data": None}

    content = await file.read()
    try:
        profile = analysis_resume(content, file.filename)
    except ValueError as e:
        return {"code": 400, "msg": str(e), "data": None}
    except Exception as e:
        return {"code": 500, "msg": f"解析失败: {e}", "data": None}

    profile_dict = profile.model_dump()
    await save_resume_to_student(email, profile_dict)

    return {"code": 200, "msg": "解析成功", "data": profile_dict}
