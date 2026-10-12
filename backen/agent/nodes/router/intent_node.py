from langgraph.types import Command
from models.my_model import MyModel, INTERNAL_TAG
from agent.state.messages_state import MessagesState
from agent.prompts.builder_prompt import BuilderPrompt
from utils.json_utils import parse_json_block

"""
意图识别判断走哪个节点
"""

prompt = BuilderPrompt.get_prompt("router/intent.yaml")

async def intent_node(state: MessagesState):
    print("[节点] intent: 开始")
    user_input = state["messages"][-1].content
    #带上最近几轮对话作为上下文来帮助识别
    history = [
        m.content for m in state["messages"][-5:-1]
        if getattr(m, "content", None)
    ]
    context = "\n".join(history[-4:])
    human_text = f"最近对话：\n{context}\n\n当前输入：{user_input}" if context else user_input
    model = MyModel.get_model()
    print("[节点] intent: 调用意图识别模型...")
    rs = await model.ainvoke([
        ("system", prompt),
        ("human", human_text),
    ], config={"tags": [INTERNAL_TAG]})  # 输出是 JSON，不让用户看到
    print("[节点] intent: 意图识别模型返回")
    # 处理返回，含兜底
    data = parse_json_block(rs.content)
    route = data.get("intent", "normal_chat")
    print(f"[节点] intent: route={route}")
    if route == "career_planning":
        return Command(
            goto="career_manager",
            update={"current_domain": "career_planning"},
        )
    if route == "interview":
        return Command(
            goto="interview_manager",
            update={"current_domain": "interview"},
        )
    if route == "job_search":
        return Command(
            goto="job_manager",
            update={"current_domain": "job_search"},
        )
    return Command(
        goto="normal_chat",
        update={"current_domain": ""},
    )