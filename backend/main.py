import logging
import os
from typing import Any, Dict, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .llm import GymLLM
from .memory import session_manager
from .middleware import RateLimiter

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/app/logs/gym-llm.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FitLife Gym Manager LLM",
    version="1.0.0",
    description="Gemini LLM bilan sport zal menejeri",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimiter)

# LLM initialization
try:
    llm = GymLLM(
        provider=os.getenv("LLM_PROVIDER", "gemini"),
        model=os.getenv("LLM_MODEL", "gemini-1.5-flash"),
        api_key=os.getenv("GEMINI_API_KEY", ""),
    )
    logger.info(f"✅ LLM initialized: {llm.provider} - {llm.model}")
except Exception as e:
    logger.error(f"❌ LLM initialization failed: {e}")
    raise


class ChatRequest(BaseModel):
    session_id: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    debug: Optional[Dict[str, Any]] = None


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ichki server xatosi. Keyinroq urinib ko'ring."},
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        if not req.session_id.strip():
            raise HTTPException(status_code=400, detail="session_id talab qilinadi")

        if not req.message.strip():
            raise HTTPException(
                status_code=400, detail="message bo'sh bo'lishi mumkin emas"
            )

        # Rate limiting check (oddiy variant)
        if len(req.message) > 1000:
            raise HTTPException(
                status_code=400, detail="Xabar juda uzun (max 1000 belgi)"
            )

        history = session_manager.get(req.session_id, [])
        trimmed_history = history[-8:]  # Oxirgi 8 xabar (Gemini uchun context limit)

        logger.info(
            f"Chat request: session={req.session_id[:10]}..., msg_len={len(req.message)}"
        )

        answer, raw = llm.generate(trimmed_history, req.message)

        # Yangi xabarlarni saqlash
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": answer})
        session_manager.set(req.session_id, history, ttl=1800)  # 30 min

        return ChatResponse(
            session_id=req.session_id,
            answer=answer,
            debug={
                "tokens": raw.get("usage", {}),
                "model": llm.model,
                "provider": llm.provider,
                "history_length": len(history),
                "finish_reason": raw.get("finish_reason"),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Xato yuz berdi. Keyinroq urinib ko'ring."
        )


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    session_manager.delete(session_id)
    logger.info(f"Session cleared: {session_id[:10]}...")
    return {"message": "Session tozalandi"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "provider": llm.provider,
        "model": llm.model,
        "timestamp": "2025-09-10 08:09:38",
    }


@app.get("/api/stats")
async def stats():
    """API statistikasi (oddiy variant)"""
    return {
        "active_sessions": len(session_manager.memory)
        if hasattr(session_manager, "memory")
        else 0,
        "provider": llm.provider,
        "model": llm.model,
    }


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "0") == "1",
    )
