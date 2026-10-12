import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.deps import get_graph

chat_router = APIRouter()


class SessionSchema(BaseModel):
    user_id: str = "1"
    session_id: str = ""


@chat_router.post("/create_session")
async def create_session(request: Request, session: SessionSchema):
    graph = get_graph(request)
    ok, reason = await graph.sessions.check_session(session.user_id, session.session_id)
    if ok:
        return {"code": 200, "msg": reason, "data": session.session_id}

    new_id = await graph.sessions.create_session(session.user_id, session.session_id or None)
    return {"code": 200, "msg": "新建会话", "data": new_id}


@chat_router.get("/chat")
async def chat(request: Request, question: str, user_id: str = "", session_id: str = "", email: str = ""):
    graph = get_graph(request)

    async def generate():
        try:
            async for chunk in graph.chat(question, user_id, session_id, email):
                data = {"data": chunk, "done": False}
                yield f"data:{json.dumps(data, ensure_ascii=False)}\n\n"
            data = {"data": "", "done": True}
            yield f"data:{json.dumps(data, ensure_ascii=False)}\n\n"
        except Exception as e:
            data = {"data": f"流式异常: {e}", "done": True}
            yield f"data:{json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
