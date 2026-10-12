import os
import aiomysql
from dotenv import load_dotenv
load_dotenv()

# 模块级单例连接池
_pool = None


async def open_mysql_pool() -> aiomysql.Pool:

    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT") or 3306),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            db=os.getenv("MYSQL_DATABASE"),
            charset=os.getenv("MYSQL_CHARSET") or "utf8mb4",
            autocommit=True,
            minsize=1,          # 注意：aiomysql 的参数名无下划线
            maxsize=20,
            connect_timeout=5,
        )
        print("MySQL 连接池已打开")
    return _pool


async def close_mysql_pool() -> None:

    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
        print("MySQL 连接池已关闭")


async def _get_mysql_pool() -> aiomysql.Pool:

    if _pool is None:
        return await open_mysql_pool()
    return _pool


async def query(sql: str, params: tuple = ()) -> list:

    pool = await _get_mysql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()


