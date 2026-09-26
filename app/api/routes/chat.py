import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_rag
from app.core.config import get_settings
from app.core.rate_limit import InMemoryRateLimiter
from app.models.chat import ChatRequest
from app.rag.pipeline import QalbuRAG

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)
rate_limiter = InMemoryRateLimiter(get_settings().chat_rate_limit_per_minute)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_rate_limit(request: Request) -> None:
    if not rate_limiter.allow(_client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail={"code": "RATE_LIMITED", "message": "Coba lagi dalam satu menit."},
        )


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/api/v1/chat", response_class=StreamingResponse)
async def stream_chat(
    request: ChatRequest,
    http_request: Request,
    rag: QalbuRAG = Depends(get_rag),  # noqa: B008
) -> StreamingResponse:
    _check_rate_limit(http_request)
    request_id = str(uuid4())

    async def events():
        try:
            async with asyncio.timeout(get_settings().request_timeout_seconds):
                async for event, payload in rag.stream_events(request, request_id):
                    yield _sse(event, payload)
        except TimeoutError:
            logger.warning("stream_chat_timeout request_id=%s", request_id)
            yield _sse(
                "error",
                {
                    "code": "REQUEST_TIMEOUT",
                    "message": "Proses refleksi melewati batas waktu. Coba lagi.",
                    "request_id": request_id,
                },
            )
            yield _sse("done", {"request_id": request_id, "profile": "unknown"})
        except Exception:
            logger.exception("stream_chat_failed request_id=%s", request_id)
            yield _sse(
                "error",
                {
                    "code": "RAG_UNAVAILABLE",
                    "message": "Layanan refleksi belum dapat dihubungi.",
                    "request_id": request_id,
                },
            )
            yield _sse("done", {"request_id": request_id, "profile": "unknown"})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )
