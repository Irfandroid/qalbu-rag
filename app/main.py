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

configure_logging()
settings = get_settings()
app = FastAPI(title="Qalbu API", version="0.1.0")


@app.middleware("http")
async def prevent_stale_frontend(request: Request, call_next):
    response = await call_next(request)
    if request.url.path in {"/", "/index.html"}:
        response.headers["Cache-Control"] = "no-store"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(chat_router)
app.include_router(dataset_router)
app.include_router(health_router)


@app.get("/dataset", include_in_schema=False)
async def dataset_page() -> FileResponse:
    return FileResponse(Path("frontend/dataset.html"))


@app.get("/dataset/verse/{surah}/{ayah}", include_in_schema=False)
async def dataset_verse_page(surah: int, ayah: int) -> FileResponse:
    return FileResponse(Path("frontend/dataset-detail.html"))


app.mount("/", StaticFiles(directory=Path("frontend"), html=True), name="frontend")
