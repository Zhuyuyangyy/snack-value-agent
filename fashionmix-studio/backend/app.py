"""
FashionMix Studio V0.2 FastAPI backend.

Endpoints:
  GET  /api/health       — health check
  POST /api/style-advice — outfit scoring (LLM w/ rule fallback)
"""

import logging
from typing import Any

from dotenv import load_dotenv
from fastapi import Body, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import style_advice

load_dotenv()
logging.basicConfig(level=logging.INFO)

limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])

app = FastAPI(title="FashionMix Studio API", version="0.2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "null",  # file:// protocol
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ItemIn(BaseModel):
    id: str
    name: str = ""
    category: str
    slot: str
    price: float
    styleTags: list[str] = Field(default_factory=list)
    riskTags: list[str] = Field(default_factory=list)
    photoScore: int = 70
    dailyScore: int = 70
    qualityScore: int = 70


class AdviceRequest(BaseModel):
    items: list[ItemIn]
    intent: str | None = None


class AdviceResponse(BaseModel):
    scores: dict[str, int]
    styleTags: list[str]
    riskTags: list[str]
    suggestion: str
    source: str


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/style-advice", response_model=AdviceResponse)
@limiter.limit("10/minute")
def style_advice_endpoint(request: Request, body: AdviceRequest = Body(...)) -> Any:
    items = [item.model_dump() for item in body.items]
    result = style_advice.get_advice(items, body.intent)
    return result
