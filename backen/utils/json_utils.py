import json

"""
LLM 返回内容的 JSON 解析工具

统一处理大模型常见的几种"非标准 JSON"输出：
  - 包裹在 ```json ... ``` 代码块里
  - 包裹在 ``` ... ``` 代码块里
  - 前后有多余空白 / 换行
  - 解析失败时返回默认值（不抛异常）

"""


def strip_code_fence(raw: str) -> str:
    """剥掉 LLM 输出外层的 ``` 代码块标记"""
    if not raw:
        return ""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def parse_json_block(raw: str, default=None):
    """把 LLM 返回的文本解析成 dict，失败返回 default（默认 {}）

    例：
        data = parse_json_block(rs.content)
        job = data.get("job", "")
    """
    if default is None:
        default = {}
    text = strip_code_fence(raw)
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def to_int(value, default: int = 0, min_value: int | None = None,
           max_value: int | None = None) -> int:
    """把 LLM 返回的值安全转成 int（兼容 "5" / 5 / "5.0" / "1万"）

    - 无法转换 -> 返回 default
    - 超出 [min_value, max_value] -> 返回 default
    """
    try:
        if isinstance(value, str) and "万" in value:
            n = int(float(value.replace("万", "").strip()) * 10000)
        else:
            n = int(float(value))
    except (TypeError, ValueError):
        return default

    if min_value is not None and n < min_value:
        return default
    if max_value is not None and n > max_value:
        return default
    return n


def to_bool(value) -> bool:
    """把 LLM 可能返回的各种 true/false 表示归一化成 bool"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "是")
    return bool(value)

def json_to_list(value) -> list:
    """把 jsonb 字段值（可能是 str/list）安全转成 list"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    return []
