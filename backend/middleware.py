import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp


class RateLimiter:
    def __init__(self, app: ASGIApp):
        self.app = app
        self.requests = defaultdict(list)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            if request.url.path.startswith("/api/"):
                session_id = request.query_params.get("session_id")
                if session_id:
                    if not self.is_allowed(session_id):
                        response = JSONResponse(
                            {"detail": "Rate limit exceeded. Try again later."},
                            status_code=429,
                        )
                        await response(scope, receive, send)
                        return
        await self.app(scope, receive, send)

    def is_allowed(self, session_id: str, limit: int = 15, window: int = 60) -> bool:
        """15 requests per minute per session"""
        now = time.time()

        # Clean old requests
        self.requests[session_id] = [
            req_time
            for req_time in self.requests[session_id]
            if now - req_time < window
        ]

        if len(self.requests[session_id]) >= limit:
            return False

        self.requests[session_id].append(now)
        return True
