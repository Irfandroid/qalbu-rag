"""FastAPI bootstrap: middleware, routers, and static frontend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.chat import router as chat_router
from app.api.routes.dataset import router as dataset_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.postgres import close_pool, get_pool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
NO_STORE_PATHS = frozenset({"/", "/index.html"})

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if settings.configured_for_rag:
        await get_pool(settings)
    yield
    await close_pool()


app = FastAPI(title="Qalbu API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def prevent_stale_frontend(request: Request, call_next):
    response = await call_next(request)
    if request.url.path in NO_STORE_PATHS:
        response.headers["Cache-Control"] = "no-store"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(chat_router)
app.include_router(dataset_router)
app.include_router(health_router)


@app.get("/dataset", include_in_schema=False)
async def dataset_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dataset.html")


@app.get("/dataset/verse/{surah}/{ayah}", include_in_schema=False)
async def dataset_verse_page(surah: int, ayah: int) -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dataset-detail.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
