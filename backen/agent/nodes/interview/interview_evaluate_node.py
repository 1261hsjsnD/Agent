from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END
from langgraph.types import Command

from agent.prompts.builder_prompt import BuilderPrompt
from agent.state.messages_state import MessagesState
from db.interview_db import update_interview_ability
from models.my_model import MyModel, INTERNAL_TAG

"""
评价节点：流式生成面试评价报告（打字机）+ 更新面试能力画像
"""
prompt = BuilderPrompt.get_prompt("interview/interview_evaluate_node.yaml")

# 面试能力画像提取提示词
ability_prompt = BuilderPrompt.get_prompt("interview/interview_evaluate_ability_node.yaml")


async def interview_evaluate_node(state: MessagesState) -> Command | dict:
    question_list = state.get("questions", [])
    user_answer_list = state.get("user_answer_list", [])
    email = state.get("user_email", "")

    # 防御：没有题目或没有作答 -> 不调 LLM，直接给友好提示并结束
    # （否则 LLM 会输出一大段"未提供任何可评估内容"的无意义报告）
    if not question_list or not user_answer_list:
        reply = "本轮面试没有有效的题目或作答记录，无法生成评价。请重新开始一次面试～"
        get_stream_writer()(reply)
        return Command(goto=END, update={
            "messages": [AIMessage(content=reply)],
            "interview_step": "done",
            "current_domain": "",
        })

    question = f"用户问题列表:{question_list}\n用户答案列表:{user_answer_list}"

    model = MyModel.get_model()

    # 1. 生成评价报告

    rs = await model.ainvoke([
        ("system", prompt),
        ("human", question),
    ])
    report = rs.content

    # 2. 生成面试能力画像并写库，打上 INTERNAL_TAG

    if email:
        try:
            rs2 = await model.ainvoke([
                ("system", ability_prompt),
                ("human", question),
            ], config={"tags": [INTERNAL_TAG]})
            ability_text = rs2.content.strip()
            await update_interview_ability(email, ability_text)
        except Exception:
            pass  # 能力画像更新失败不影响评价返回

    return {
        "messages": [AIMessage(content=report)],
        "evaluation": report,
        "interview_step": "done",
    }
