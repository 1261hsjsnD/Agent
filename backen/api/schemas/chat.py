from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    user_id: str = ""
    session_id: str = ""
    email: str = ""


class ChatResponse(BaseModel):
    data: str
    done: bool = False
