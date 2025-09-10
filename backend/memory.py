import json
import os
from typing import Any, Dict, List

import redis


class SessionManager:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()  # Test connection
                self.use_redis = True
                print("✅ Redis bilan ulandi")
            except Exception:
                print("⚠️  Redis ga ulanib bo'lmadi, in-memory ishlatiladi")
                self.use_redis = False
                self.memory = {}
        else:
            self.use_redis = False
            self.memory = {}

    def get(self, session_id: str, default=None) -> List[Dict[str, Any]]:
        if self.use_redis:
            try:
                data = self.redis_client.get(f"session:{session_id}")
                return json.loads(data) if data else (default or [])
            except Exception:
                return default or []
        else:
            return self.memory.get(session_id, default or [])

    def set(self, session_id: str, data: List[Dict[str, Any]], ttl: int = 3600):
        if self.use_redis:
            try:
                self.redis_client.setex(
                    f"session:{session_id}", ttl, json.dumps(data, ensure_ascii=False)
                )
            except Exception as e:
                print(f"⚠️  Redis error: {e}")
                self.memory[session_id] = data
        else:
            self.memory[session_id] = data

    def delete(self, session_id: str):
        if self.use_redis:
            try:
                self.redis_client.delete(f"session:{session_id}")
            except Exception as e:
                print(f"⚠️  Redis error: {e}")
                self.memory.pop(session_id, None)
        else:
            self.memory.pop(session_id, None)


session_manager = SessionManager()
