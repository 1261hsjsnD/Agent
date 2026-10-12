from langchain.tools import tool
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import pymysql

load_dotenv()


class MySQLSchema(BaseModel):
    """mysql_tool 的参数 schema"""
    sql: str = Field(..., description="要执行的 SQL 查询语句")


@tool("mysql_tool", args_schema=MySQLSchema)
def mysql_tool(sql: str) -> str:
    """
    执行 sql 语句查询（MySQL）
    数据库：agent
    相关表：
        job_category  岗位表，字段：id、job_name、subjects（逗号分隔的科目）
        question_bank 题库表，字段：id、subject、question、answer
    规则：
        - 禁止生成 DELETE, UPDATE, INSERT, DROP, CREATE, ALTER 语句
        - 只允许 SELECT 查询
    """
    con = None
    cursor = None
    try:
        host = os.getenv("MYSQL_HOST")
        port = os.getenv("MYSQL_PORT")
        user = os.getenv("MYSQL_USER")
        password = os.getenv("MYSQL_PASSWORD")
        db_name = os.getenv("MYSQL_DATABASE")
        if not host or not port or not user or not password or not db_name:
            return "数据库连接参数未配置"

        # 兜底：拦截写操作
        sql_upper = sql.upper()
        if any(k in sql_upper for k in ("DELETE", "UPDATE", "INSERT", "DROP", "CREATE", "ALTER")):
            return "禁止执行非法sql语句操作"

        con = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            db=db_name,
            charset="utf8mb4",
        )
        cursor = con.cursor()
        cursor.execute(sql)
        rs = cursor.fetchall()
        return str(rs)
    except Exception as e:
        return f"查询失败: {e}"
    finally:
        if cursor:
            cursor.close()
        if con:
            con.close()


if __name__ == '__main__':
    print(mysql_tool.invoke({"sql": "select * from job_category limit 3"}))
