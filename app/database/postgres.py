"""Local PostgreSQL (pgvector) connection pool."""

import asyncio
import json

import asyncpg

from app.core.config import Settings

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def _init_connection(connection: asyncpg.Connection) -> None:
    # asyncpg returns json/jsonb as text unless a codec is registered.
    for type_name in ("json", "jsonb"):
        await connection.set_type_codec(
            type_name,
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )


async def get_pool(settings: Settings) -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        if _pool is None:
            if not settings.database_url:
                raise RuntimeError("DATABASE_URL is not configured")
            _pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=1,
                max_size=5,
                timeout=10,
                command_timeout=settings.request_timeout_seconds,
                init=_init_connection,
            )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
