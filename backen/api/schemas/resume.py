from pydantic import BaseModel


class ResumeUploadRequest(BaseModel):
    email: str
