from psycopg_pool import AsyncConnectionPool
import os
from dotenv import load_dotenv
load_dotenv()
_pool = None


def get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=(
                f"host={os.getenv('POSTGRESQL_HOST')} "
                f"port={os.getenv('POSTGRESQL_PORT')} "
                f"dbname={os.getenv('POSTGRESQL_DATABASE')} "
                f"user={os.getenv('POSTGRESQL_USER')} "
                f"password={os.getenv('POSTGRESQL_PASSWORD')} "
                "connect_timeout=3"
            ),
            min_size=1,
            max_size=20,
            open=False,          # 手动 open，配合 lifespan 启动
            timeout=5,           # 从池里取连接的等待超时
        )
    return _pool

#打开连接池
async def open_pool():
    await get_pool().open()

#关闭连接池

async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

#获取数据库一个连接
async def get_pg_conn():
    return await get_pool().getconn()

#释放数据库连接
async def release_pg_conn(conn):
    if conn is not None:
        await get_pool().putconn(conn)
