import asyncio

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, AIMessageChunk
from langgraph.graph import StateGraph, START, END

from agent.state.messages_state import MessagesState
from agent.memory.manager.session_manager import SessionManager
from agent.memory.manager.memory_manager import MemoryManager
from services.session_service import (
    SessionService, SessionBusyError, SESSION_NOT_FOUND,
)
from db.dao.redis import get_redis
from models.my_model import INTERNAL_TAG

# 路由节点
from agent.nodes.router.main_manager_node import main_manager_node
from agent.nodes.router.intent_node import intent_node
from agent.nodes.normal_chat_node import normal_chat_node
# 职业规划域
from agent.nodes.career.career_manager_node import career_manager_node
from agent.nodes.career.career_recommend_node import career_recommend_node
from agent.nodes.career.career_plan_node import career_plan_node
# 面试域
from agent.nodes.interview.interview_manager_node import interview_manager_node
from agent.nodes.interview.interview_intent_node import interview_intent_node
from agent.nodes.interview.interview_question_node import interview_question_node
from agent.nodes.interview.interview_answer_node import interview_answer_node
from agent.nodes.interview.interview_evaluate_node import interview_evaluate_node
# 找工作域
from agent.nodes.job.job_manager_node import job_manager_node
from agent.nodes.job.job_intent_node import job_intent_node
from agent.nodes.job.job_search_node import job_search_node


class Graph:
    def __init__(self, checkpoint, redis=None):
        self.memory = checkpoint
        # Redis 客户端（会话校验 分布式会话锁  窗口记忆）
        self.redis = redis or get_redis()
        self.sessions = SessionService(self.redis)
        # 后台记忆更新：
        self._pending_updates: dict = {}
        #会话锁
        self._update_locks: dict = {}
        self.agent = self.get_agent()

    def _get_update_lock(self, session_id: str) -> asyncio.Lock:
        """获取（或创建）某个 session 的记忆更新锁"""
        if session_id not in self._update_locks:
            self._update_locks[session_id] = asyncio.Lock()
        return self._update_locks[session_id]

    def get_agent(self):
        graph = StateGraph(MessagesState)
        # 添加节点
        graph.add_node("main_manager", main_manager_node)
        graph.add_node("intent", intent_node)
        graph.add_node("normal_chat", normal_chat_node)
        graph.add_node("career_manager", career_manager_node)
        graph.add_node("career_recommend", career_recommend_node)
        graph.add_node("career_plan", career_plan_node)
        graph.add_node("interview_manager", interview_manager_node)
        graph.add_node("interview_intent", interview_intent_node)
        graph.add_node("interview_question", interview_question_node)
        graph.add_node("interview_answer", interview_answer_node)
        graph.add_node("interview_evaluate", interview_evaluate_node)
        graph.add_node("job_manager", job_manager_node)
        graph.add_node("job_intent", job_intent_node)
        graph.add_node("job_search", job_search_node)

        # 入口：统一走 main_manager，由它决定"识别意图"还是"进入进行中的域"
        graph.add_edge(START, "main_manager")

        # 业务节点执行完都回各自的 manager（返回 dict的，走 add_edge）
        # manager 用 Command 集中决定下一步跳转
        graph.add_edge("normal_chat", END)
        graph.add_edge("career_recommend", "career_manager")
        graph.add_edge("interview_intent", "interview_manager")
        graph.add_edge("interview_question", "interview_manager")
        graph.add_edge("interview_answer", "interview_manager")
        graph.add_edge("interview_evaluate", "interview_manager")
        graph.add_edge("job_intent", "job_manager")
        # 编译（由 __init__ 统一赋值给 self.agent，这里只负责构建并返回）
        return graph.compile(checkpointer=self.memory)

    async def chat(self, question, user_id, session_id, email=""):
        print(f"进入聊天:用户问题：{question},用户ID:{user_id},会话ID:{session_id},邮箱:{email}")
        # 用 email 作为记忆的 user_id（画像记忆按 email 定位）；没有 email 则用 user_id
        memory_user_id = email or str(user_id)

        # ---------- 会话校验 ----------
        ok, reason = await self.sessions.check_session(user_id, session_id)
        if not ok:
            if reason == SESSION_NOT_FOUND:
                await self.sessions.create_session(user_id, session_id)
                print(f"[会话] 首次访问，自动创建会话: {session_id}")
            else:
                print(f"[会话] 校验失败: {reason}")
                yield f"[会话不可用] {reason}"
                return
        # 等待上一轮的后台记忆更新完成
        prev_task = self._pending_updates.get(session_id)
        if prev_task and not prev_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(prev_task), timeout=3)
            except (asyncio.TimeoutError, Exception) as e:
                print(f"[记忆] 等待上一轮更新超时/异常，继续本轮: {e}")

        # 记录 AI 回答
        ai_answer = ""
        session_manager = None

        try:
            # 同一 session 同一时刻只允许一个请求进入，避免两条流同时读写
            # 同一份窗口记忆 / LangGraph checkpoint
            async with self.sessions.session_lock(session_id):
                # ---------- 记忆：读 + 存用户消息 ----------
                print("[记忆] 1-创建 SessionManager...")
                session_manager = SessionManager(session_id, memory_user_id)
                print("[记忆] 2-SessionManager 创建完成，保存用户消息...")
                await session_manager.save("user", question)
                print("[记忆] 3-用户消息已保存，构建 prompt...")
                memory_prompt = await session_manager.build_prompt(memory_user_id, question)
                print("[记忆] 4-prompt 构建完成")

                # 构建用户问题（记忆作为 system 消息注入，email 带入 state）
                user_msg = {
                    "messages": [SystemMessage(content=memory_prompt), HumanMessage(content=question)],
                    "user_email": email,
                    "user_id": user_id,
                }
                # 配置检测点
                config = {"configurable": {"thread_id": session_id}}

                #   messages -> 节点内 LLM 调用的逐 token（callback 机制自动冒泡，打字机）
                #   custom   - 节点里手动 writer() 写的固定提示文本

                STREAM_NODES = {
                    "normal_chat",        # 正常聊天
                    "career_recommend",   # 岗位推荐
                    "career_plan",        # 职业规划
                    "interview_evaluate", # 面试评价
                    "job_search",         # 找工作推荐报告
                }
                # 去重补发的完整消息
                streamed_nodes = set()

                async for mode, chunk in self.agent.astream(
                    user_msg, config,
                    stream_mode=["messages", "custom"],
                ):
                    if mode == "messages":
                        msg, meta = chunk
                        node = meta.get("langgraph_node", "")
                        if node not in STREAM_NODES:
                            continue
                        # 拦截内部不展示给用户的消息
                        if INTERNAL_TAG in meta.get("tags", []):
                            continue

                        # 去重：messages 通道在 LLM 调用结束时会额外补发一条
                        if isinstance(msg, AIMessageChunk):
                            if msg.content:
                                streamed_nodes.add(node)
                                ai_answer += msg.content
                                yield msg.content
                        elif isinstance(msg, AIMessage) and msg.content and node not in streamed_nodes:
                            ai_answer += msg.content
                            yield msg.content
                    else:
                        # custom 通道：节点手动 writer() 的固定文本
                        content = str(chunk)
                        if content:
                            yield content

                # 保存 AI 回复放在锁内：下一条请求要读窗口记忆，必须等它落库，
                # 否则会丢一轮上下文
                print("[记忆] 5-流式结束，保存 AI 回复...")
                if ai_answer:
                    await session_manager.save("ai", ai_answer)
        except SessionBusyError as e:
            print(f"[会话] {e}")
            yield str(e)
            return

        # ---------- 记忆：更新（后台任务，不阻塞用户响应）----------
        # 长期 / 摘要是"对历史的提炼"，滞后一轮写入不影响正确性。
        # 后台化后，流一结束用户即可发送下一条，无需等待记忆更新完成。
        # 加锁保证同一 session 的后台更新串行，避免摘要"读-改-写"覆盖竞态。
        print("[记忆] 6-提交后台记忆更新...")
        memory_manager = MemoryManager(session_manager)
        update_lock = self._get_update_lock(session_id)

        async def _bg_update_memory():
            try:
                async with update_lock:
                    await memory_manager.update(memory_user_id)
                    print("[记忆] 7-记忆更新完成")
            except Exception as e:
                print(f"[记忆] 后台更新失败: {e}")

        self._pending_updates[session_id] = asyncio.create_task(_bg_update_memory())

    def draw(self):
        data = self.agent.get_graph().draw_mermaid_png()
        with open("考试图.png", "wb") as f:
            f.write(data)
