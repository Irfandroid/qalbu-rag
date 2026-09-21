import json
import logging
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_rag
from app.core.config import get_settings
from app.core.rate_limit import InMemoryRateLimiter
from app.models.chat import ChatRequest, ErrorResponse, QalbuResponse
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
            async for event, payload in rag.stream_events(request, request_id):
                yield _sse(event, payload)
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
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/api/chat",
    response_model=QalbuResponse,
    responses={
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def chat(
    request: ChatRequest,
    http_request: Request,
    rag: QalbuRAG = Depends(get_rag),  # noqa: B008
) -> QalbuResponse:
    _check_rate_limit(http_request)
    request_id = str(uuid4())
    try:
        return await rag.ask(request.message.strip(), request_id)
    except RuntimeError as exc:
        logger.warning("chat_unavailable request_id=%s", request_id)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RAG_UNAVAILABLE",
                "message": "Qalbu retrieval service is unavailable.",
            },
        ) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        logger.warning("provider_request_failed request_id=%s status=%s", request_id, status_code)
        raise HTTPException(
            status_code=503 if status_code in {429, 500, 502, 503, 504} else 502,
            detail={
                "code": "AI_PROVIDER_UNAVAILABLE",
                "message": ("AI provider is temporarily unavailable. Please try again shortly."),
            },
        ) from exc
    except httpx.RequestError as exc:
        logger.warning("provider_connection_failed request_id=%s", request_id)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AI_PROVIDER_UNAVAILABLE",
                "message": (
                    "AI provider is not running or cannot be reached. Start Ollama and try again."
                ),
            },
        ) from exc
    except Exception as exc:
        logger.exception("chat_failed request_id=%s", request_id)
        raise HTTPException(
            status_code=502,
            detail={
                "code": "GENERATION_FAILED",
                "message": "Unable to generate a grounded response.",
            },
        ) from exc
