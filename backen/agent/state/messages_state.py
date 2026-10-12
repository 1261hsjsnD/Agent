import operator
from typing_extensions import TypedDict, Annotated, Any
from langchain_core.messages import AnyMessage

class MessagesState(TypedDict):
    # AI 消息列表
    messages: Annotated[list[AnyMessage], operator.add]
    # 当前路由 面试：interview 职业规划：career_planning 正常聊天：chat
    current_domain: str = ""
    # ----------面试路由----------
    # 面试岗位名（用户说的岗位，如 后端开发）
    job_name: str = ""
    # 面试科目列表（用户选的科目，如 ['python', 'mysql']，支持双科目混合）
    subjects: list = []
    # 题目数量
    total: int = 0
    # 题库列表
    questions: list = []
    # 当前题目
    current_question: str = ""
    # 用户答案列表
    user_answer_list: list = []
    # 当前答题的题目索引
    current_id: int = 0
    # 评价结果
    evaluation: str = ""
    # 考试状态
    interview_step: str = ""
    # 当前题目编号
    question_id: int = 0
    # 是否继续出题
    continue_question: bool = False
    # ----------职业规划路由----------
    # 用户ID
    user_id: str = ""
    # 用户邮箱（登录后用于定位画像）
    user_email: str = ""
    # 职业规划流程状态：
    #   ""          首次进入，读画像判断
    #   recommend   已推荐岗位方向，等用户选择
    #   plan        画像+岗位齐全，出规划
    career_step: str = ""
    # 用户画像（从数据库加载的专业、技能、年级、目标岗位等）
    user_profile: dict = {}
    # 年级（大一/大二/大三/大四/研一/研二/研三）
    grade: str = ""
    # 推荐给用户的候选岗位方向列表（来自 major_job_match 表）
    recommend_jobs: list = []
    # ----------找工作（岗位行情查询）路由----------
    # 工作查询流程状态：
    #   ""          首次进入，提取条件
    #   ask_more    信息不全（缺岗位），已追问，等用户补充
    #   done        查询完成
    job_step: str = ""
    # 用户想找的岗位关键词（必填，如 后端开发）
    search_job: str = ""
    # 期望城市（可空，空则不限）
    search_city: str = ""
    # 期望薪资下限/上限（元，0 表示不限）
    search_salary_min: int = 0
    search_salary_max: int = 0
    # 岗位名映射结果（方向 -> job 表真实岗位名，如 后端开发 -> [Java, C/C++]）
    search_job_names: list = []



