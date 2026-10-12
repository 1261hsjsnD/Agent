import asyncio
import os
import sys
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from db.dao.mysql import open_mysql_pool, close_mysql_pool
from api.router import api_router
from db.dao.postgres import open_pool, close_pool
from db.dao.redis import close_redis, get_redis
from agent.graph.graph import Graph
load_dotenv()

# 简历模板静态目录：storage/resumes
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(_BASE_DIR, "storage", "resumes")
TEMPLATE_DIR_NAME = "templates"

# LangGraph checkpoint 存放的数据库连接串
POSTGRESQL_URL = os.getenv("POSTGRESQL_URL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_pool()
    await open_mysql_pool()
    print("数据库连接池已打开")

    # 初始化 Graph 并挂到 app.state.graph
    # checkpoint 用 PostgreSQL 持久化（幂等 setup，首次会自动建表）
    async with AsyncPostgresSaver.from_conn_string(POSTGRESQL_URL) as saver:
        await saver.setup()
        redis_client = get_redis()
        app.state.graph = Graph(saver, redis=redis_client)
        print("AI 智能体创建成功（checkpoint 已持久化到 PostgreSQL）")
        yield

    await close_redis()
    await close_mysql_pool()
    await close_pool()
    print("数据库连接池已关闭，Redis 连接池已关闭")


app = FastAPI(lifespan=lifespan)

# 前端约定的路径不带 /api/v1 前缀（如 /login/login、/chat/chat）
app.include_router(api_router)

# 简历模板静态目录
os.makedirs(TEMPLATE_DIR, exist_ok=True)
app.mount(
    f"/resume/{TEMPLATE_DIR_NAME}",
    StaticFiles(directory=TEMPLATE_DIR),
    name="resume_templates",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}
