import os
import uuid
import asyncio

import chromadb
from dotenv import load_dotenv

load_dotenv()

"""
长期记忆 - 向量存储（ChromaDB）

email 说明：由上层传入的是 graph.py 的 memory_user_id（= email or str(user_id)），
有登录态时就是 email。ChromaDB 的元数据字段名沿用 "user_id" 以保持历史数据兼容。
"""


class LongMemory:
    def __init__(self):
        path = os.getenv("CHROM_PATH")
        self.client = chromadb.PersistentClient(path)
        self.collection = self.client.get_or_create_collection("long_memory")

    async def save(self, email, query: str):
        """保存一条长期记忆"""
        email = str(email)
        memory_id = f"memory_{email}+{uuid.uuid4()}"
        # chromadb 是同步的，丢线程池执行

        await asyncio.to_thread(
            self.collection.add,
            ids=[memory_id],
            documents=[query],
            metadatas=[{"user_id": email}],
        )

    async def query(self, email, question: str, n_results: int = 3) -> list:
        """检索相关的长期记忆"""
        email = str(email)
        rs = await asyncio.to_thread(
            self.collection.query,
            query_texts=[question],
            n_results=n_results,
            where={"user_id": email},
        )
        docs = rs.get("documents") or [[]]
        return docs[0] if docs else []
