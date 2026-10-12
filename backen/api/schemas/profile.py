from pydantic import BaseModel


class ProfileSchema(BaseModel):
    email: str
    name: str = ""
    grade: str = ""
    major: str = ""
    target_job: str = ""


class StudentModel(BaseModel):
    email: str
    student: dict
