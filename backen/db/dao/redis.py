import redis.asyncio as redis
import os
from dotenv import load_dotenv
load_dotenv()
_client = None

def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            db=int(os.getenv("REDIS_DB")),
            password=os.getenv("REDIS_PASSWORD")    ,
            decode_responses=True,
            protocol=2,
            socket_connect_timeout=3,
            socket_timeout=3,
            max_connections=50,
            health_check_interval=30,
        )
    return _client


async def close_redis():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
