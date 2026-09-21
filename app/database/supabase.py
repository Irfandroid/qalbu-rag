from app.core.config import Settings
from supabase import AsyncClient, acreate_client


async def get_supabase(settings: Settings) -> AsyncClient:
    if not settings.supabase_url or not settings.supabase_server_key:
        raise RuntimeError("Supabase server credentials are not configured")
    return await acreate_client(settings.supabase_url, settings.supabase_server_key)
