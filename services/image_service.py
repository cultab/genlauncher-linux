from __future__ import annotations

import io
import json
import logging
import os
import time

import httpx
from PIL import Image

from genlauncher_tui.models.mod import standard_mod_name

logger = logging.getLogger(__name__)

MAX_THUMB_WIDTH = 640
MAX_THUMB_HEIGHT = 200
RETRY_AFTER_SECONDS = 300
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


class ThumbnailService:
    def __init__(self, cache_dir: str | None = None):
        if cache_dir is None:
            from platformdirs import user_cache_dir
            cache_dir = os.path.join(user_cache_dir("genlauncher_tui"), "thumbnails")
        self._cache_dir = cache_dir
        self._failed_urls: dict[str, float] = {}
        os.makedirs(self._cache_dir, exist_ok=True)
        self._load_failed_urls()

    def _failed_urls_path(self) -> str:
        return os.path.join(self._cache_dir, "failed_urls.json")

    def _load_failed_urls(self):
        path = self._failed_urls_path()
        if not os.path.isfile(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
            now = time.time()
            self._failed_urls = {
                url: ts for url, ts in data.items()
                if now - ts < RETRY_AFTER_SECONDS
            }
        except Exception:
            pass

    def _save_failed_urls(self):
        try:
            os.makedirs(self._cache_dir, exist_ok=True)
            with open(self._failed_urls_path(), "w") as f:
                json.dump(self._failed_urls, f)
        except Exception:
            pass

    def _cache_path(self, name: str) -> str:
        return os.path.join(self._cache_dir, f"{standard_mod_name(name)}.png")

    def get_cached_path(self, name: str) -> str | None:
        path = self._cache_path(name)
        return path if os.path.isfile(path) else None

    async def fetch_thumbnail(self, url: str, name: str) -> str | None:
        if url in self._failed_urls:
            return None
        cache_path = self._cache_path(name)
        if os.path.isfile(cache_path):
            return cache_path
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers={"User-Agent": _USER_AGENT}) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            data = resp.content
            if not isinstance(data, bytes):
                self._failed_urls[url] = time.time()
                self._save_failed_urls()
                return None
            with open(cache_path, "wb") as f:
                f.write(data)
            return cache_path
        except Exception:
            self._failed_urls[url] = time.time()
            self._save_failed_urls()
            logger.exception("Failed to download thumbnail for %s", name)
            return None

    @staticmethod
    def load_and_resize(path: str) -> tuple[bytes, int, int]:
        img = Image.open(path)
        img = img.convert("RGBA")
        img.thumbnail((MAX_THUMB_WIDTH, MAX_THUMB_HEIGHT), Image.LANCZOS)
        w, h = img.size
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), w, h
