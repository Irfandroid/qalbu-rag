"""Authenticated HTTP client for the Kemenag Quran portal."""

from typing import Any

import httpx

from scripts.kemenag.config import DEFAULT_BASE_URL
from scripts.kemenag.parsing import parse_payload


class KemenagPortalClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        token: str,
        timeout: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = token
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"Accept": "application/json, text/html"},
        )

    @classmethod
    def from_settings(
        cls,
        base_url: str | None,
        username: str,
        password: str,
        token: str,
        timeout: float,
    ) -> "KemenagPortalClient":
        return cls(base_url or DEFAULT_BASE_URL, username, password, token, timeout)

    def close(self) -> None:
        self.client.close()

    def login(self) -> None:
        portal_root = self.base_url.removesuffix("/data")
        response = self.client.post(
            f"{portal_root}/dashboard/cek_login",
            data={"username": self.username, "password": self.password, "id": self.token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        if "dashboard/login" in str(response.url).casefold():
            raise RuntimeError("Kemenag login gagal; periksa username, password, dan token")

    def get_ayat(self, surah: int) -> list[dict[str, Any]]:
        response = self.client.post(f"{self.base_url}/getAyat", data={"surah": str(surah)})
        response.raise_for_status()
        return parse_payload(response)

    def get_tafsir(self, ayat_id: str) -> dict[str, Any]:
        response = self.client.post(
            f"{self.base_url}/getAyatTafsir", data={"ayat": ayat_id}
        )
        response.raise_for_status()
        return parse_payload(response)[0]
