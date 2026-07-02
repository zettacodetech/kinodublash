"""
Backend API bilan aloqa — httpx orqali. Bot faqat shu klass orqali
markaziy FastAPI xizmatiga murojaat qiladi. Katta fayllar (2GB gacha) RAM ga
sig'masligi uchun disk<->tarmoq oqim (streaming) ishlatiladi.
"""
from pathlib import Path

import httpx

from .config import settings

# Katta yuklash/yuklab olish uchun uzoq timeout
_LONG_TIMEOUT = httpx.Timeout(connect=30.0, read=None, write=None, pool=None)


class BackendClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.BACKEND_URL).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=_LONG_TIMEOUT)

    async def close(self) -> None:
        await self._client.aclose()

    async def submit_dub_file(
        self,
        file_path: str | Path,
        voice: str,
        external_id: str | None = None,
        username: str | None = None,
        full_name: str | None = None,
    ) -> str:
        """
        Videoni /dub ga OQIM orqali yuboradi (fayl RAM ga to'liq yuklanmaydi).
        task_id qaytaradi.
        """
        data = {"external_id": external_id, "username": username, "full_name": full_name}
        data = {k: v for k, v in data.items() if v is not None}
        # httpx fayl obyektini bo'lak-bo'lak o'qiydi -> katta fayl uchun xavfsiz
        with open(file_path, "rb") as f:
            files = {"file": ("video.mp4", f, "video/mp4")}
            resp = await self._client.post(
                "/dub", params={"voice": voice}, files=files, data=data
            )
        resp.raise_for_status()
        return resp.json()

    async def submit_dub_url(
        self,
        url: str,
        voice: str,
        external_id: str | None = None,
        username: str | None = None,
        full_name: str | None = None,
    ) -> str:
        """YouTube (yoki boshqa) havolani /dub-url ga yuboradi va task_id qaytaradi."""
        payload = {
            "url": url,
            "voice": voice,
            "external_id": external_id,
            "username": username,
            "full_name": full_name,
        }
        resp = await self._client.post("/dub-url", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def get_status(self, task_id: str) -> dict:
        resp = await self._client.get(f"/status/{task_id}")
        resp.raise_for_status()
        return resp.json()

    async def download_to_file(self, task_id: str, dest_path: str | Path) -> Path:
        """Tayyor videoni backenddan diskка OQIM orqali yuklab oladi (RAM tejaladi)."""
        dest_path = Path(dest_path)
        async with self._client.stream("GET", f"/download/{task_id}") as resp:
            resp.raise_for_status()
            with dest_path.open("wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=4 * 1024 * 1024):
                    f.write(chunk)
        return dest_path
