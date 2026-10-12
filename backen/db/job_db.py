from db.dao.postgres import get_pool
import re
"""
招聘岗位原始信息表
"""

# 薪资解析正则
_RE_DAY = re.compile(r"(\d+)\s*-\s*(\d+)\s*元\s*/\s*天")     # 120-150元/天
_RE_WAN = re.compile(r"([\d.]+)\s*-\s*([\d.]+)\s*万")        # 1-1.3万 / 1.5-3万·14薪
_RE_YUAN = re.compile(r"(\d+)\s*-\s*(\d+)\s*元")             # 7000-14000元 / 6000-8000元·13薪
_RE_SINGLE_WAN = re.compile(r"([\d.]+)\s*万")                # 1万
_RE_SINGLE_YUAN = re.compile(r"(\d+)\s*元")                  # 8000元


def parse_salary(salary: str):
    """把 salary 字符串解析成 (月薪下限, 月薪上限)，单位：元

    - 月薪区间："7000-14000元"   -> (7000, 14000)
    - 万元区间："1-1.3万"        -> (10000, 13000)
    - 带几薪："6000-8000元·13薪" -> (6000, 8000)   （几薪不影响月薪区间）
    - 单个值："1万" / "8000元"   -> (10000, 10000)
    - 日薪："120-150元/天"       -> ("day", 120, 150)  单独标记，不参与月薪比较
    - 无法解析（"面议"等）       -> None

    返回：
      (lo, hi) 元/月  | ("day", lo, hi) | None
    """
    if not salary:
        return None
    s = str(salary).strip()

    # 日薪：单独标记
    m = _RE_DAY.search(s)
    if m:
        return ("day", int(m.group(1)), int(m.group(2)))

    # 万元区间
    m = _RE_WAN.search(s)
    if m:
        return (int(float(m.group(1)) * 10000), int(float(m.group(2)) * 10000))

    # 元区间
    m = _RE_YUAN.search(s)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    # 单个「万」
    m = _RE_SINGLE_WAN.search(s)
    if m:
        v = int(float(m.group(1)) * 10000)
        return (v, v)

    # 单个「元」
    m = _RE_SINGLE_YUAN.search(s)
    if m:
        v = int(m.group(1))
        return (v, v)

    return None


def salary_overlap(salary: str, user_min: int, user_max: int) -> bool:
    """岗位薪资与用户期望区间是否有重叠

    用「重叠」而非「包含」：用户要 1.5-3万，岗位 2-4万 也算匹配。
    - 解析不了（面议/日薪）-> 宽松保留
    - 用户没给薪资（user_min/user_max 都为 0）-> 全保留
    """
    if not user_min and not user_max:
        return True

    parsed = parse_salary(salary)
    if not parsed:
        return True                      # 解析不了，保留
    if isinstance(parsed[0], str):       # 日薪
        return True                      # 日薪单独处理，先保留

    lo, hi = parsed
    u_lo = user_min or 0
    u_max = user_max or 10 ** 9
    return lo < u_max and hi > u_lo


async def query_all_job_names() -> list:
    """取 job 表所有去重后的岗位名（给 LLM 做方向映射用）"""
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT DISTINCT job_name FROM job WHERE job_name IS NOT NULL"
            )
            rows = await cur.fetchall()
    return [r[0] for r in rows if r[0]]


async def search_jobs(job_names: list, city: str = "", limit: int = 60) -> list:
    """按岗位名列表 + 城市查招聘岗位
    - job_names 为空 -> 返回空（岗位是必填条件）
    - city 为空 -> 不限城市
    结果按薪资解析值在 Python 侧排序（见 sort_by_salary）
    """
    if not job_names:
        return []

    sql = """
        SELECT job_name, city, district, salary, company_name,
               industry, company_size, company_type, source_url, updated_date
        FROM job
        WHERE job_name = ANY(%s)
    """
    params = [list(job_names)]

    if city:
        sql += " AND city LIKE %s"
        params.append(f"%{city}%")

    sql += " LIMIT %s"
    params.append(limit)

    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, tuple(params))
            rows = await cur.fetchall()

    return [
        {
            "job_name": r[0],
            "city": r[1],
            "district": r[2],
            "salary": r[3],
            "company_name": r[4],
            "industry": r[5],
            "company_size": r[6],
            "company_type": r[7],
            "source_url": r[8],
            "updated_date": r[9],
        }
        for r in rows
    ]


# 按薪资上限降序排序（解析不了的排最后）
def sort_by_salary(rows: list) -> list:
    def key(item):
        parsed = parse_salary(item.get("salary"))
        if not parsed or isinstance(parsed[0], str):
            return -1
        return parsed[1]

    return sorted(rows, key=key, reverse=True)
