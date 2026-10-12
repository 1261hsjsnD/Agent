from langchain_core.messages import AIMessage, SystemMessage
from langgraph.config import get_stream_writer

from agent.state.messages_state import MessagesState
from agent.prompts.builder_prompt import BuilderPrompt
from models.my_model import MyModel

"""
正常聊天节点

职责：承接意图识别为 normal_chat 的用户输入，做一轮自然的对话回复。

"""

prompt = BuilderPrompt.get_prompt("router/normal_chat.yaml")

# 携带的最近对话条数（不含 system），防止历史过长把 context 撑爆
MAX_HISTORY = 10


def _profile_text(profile: dict) -> str:
    """把用户画像压缩成一段背景说明（没有画像就不加）"""
    if not profile:
        return ""
    keys = [
        ("grade", "年级"),
        ("major", "专业"),
        ("skills", "已掌握技能"),
        ("target_job", "目标岗位"),
        ("project_experience", "项目经历"),
    ]
    parts = []
    for key, label in keys:
        value = profile.get(key)
        if not value:
            continue
        if isinstance(value, list):
            value = "、".join(str(v) for v in value)
        parts.append(f"{label}：{value}")
    return "、".join(parts)


async def normal_chat_node(state: MessagesState) -> dict:
    print("[节点] normal_chat: 开始")
    messages = state.get("messages", [])

    # 1. 最新一条 system = 本轮的记忆摘要（窗口记忆 + 长期记忆 + 用户画像）
    memory_ctx = ""
    for m in reversed(messages):
        if isinstance(m, SystemMessage):
            memory_ctx = m.content or ""
            break

    # 2. 最近 N 轮真实对话
    dialog = [m for m in messages if not isinstance(m, SystemMessage)][-MAX_HISTORY:]
    print(f"[节点] normal_chat: 携带历史 {len(dialog)} 条，记忆摘要 {len(memory_ctx)} 字")

    # 3. 组装上下文
    payload = [("system", prompt)]

    profile_text = _profile_text(state.get("user_profile", {}))
    if profile_text:
        payload.append(("system", f"这位用户的基本情况：{profile_text}"))

    if memory_ctx:
        payload.append((
            "system",
            "以下是这位用户的已知信息和近期对话摘要，只作为背景参考，不要复述或提及它的存在：\n"
            + memory_ctx
        ))

    for m in dialog:
        if not getattr(m, "content", None):
            continue
        role = "ai" if isinstance(m, AIMessage) else "human"
        payload.append((role, m.content))

    # 4. 调用模型
    model = MyModel.get_model()
    try:
        rs = await model.ainvoke(payload)
        reply = (rs.content or "").strip()
    except Exception as e:
        print(f"[节点] normal_chat: 模型调用失败 {e}")
        reply = ""

    # 5. 兜底：模型没给出内容时给一句友好回复（走 custom 通道）
    if not reply:
        reply = "抱歉，我刚才没反应过来，能再说一遍吗？你也可以直接问我职业规划或面试相关的问题～"
        get_stream_writer()(reply)
        print("[节点] normal_chat: 走兜底回复")

    print(f"[节点] normal_chat: 回复 {len(reply)} 字")
    return {
        "messages": [AIMessage(content=reply)],
        "current_domain": "",   # 保持空闲，下一轮重新识别意图
    }
