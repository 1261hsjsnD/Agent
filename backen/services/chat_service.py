"""
聊天服务：对 Graph.chat() 的薄封装

"""


class ChatService:
    def __init__(self, graph):
        self.graph = graph

    async def chat(self, question, user_id, session_id, email=""):
        async for chunk in self.graph.chat(question, user_id, session_id, email):
            yield chunk
