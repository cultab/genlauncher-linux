from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest
from PIL import Image

from genlauncher_tui.services.image_service import ThumbnailService


def _make_test_png(size=(64, 48)) -> bytes:
    img = Image.new("RGBA", size, (255, 0, 0, 255))
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestThumbnailServiceCache:
    def test_cache_path_uses_standard_name(self):
        svc = ThumbnailService(cache_dir="/tmp/test_cache")
        path = svc._cache_path("Rise of the Reds")
        assert "riseofthereds" in path
        assert path.endswith(".png")

    def test_get_cached_path_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = ThumbnailService(cache_dir=tmpdir)
            assert svc.get_cached_path("Nonexistent") is None

    def test_get_cached_path_returns_path_when_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = ThumbnailService(cache_dir=tmpdir)
            path = svc._cache_path("Test Mod")
            with open(path, "w") as f:
                f.write("dummy")
            result = svc.get_cached_path("Test Mod")
            assert result == path
            assert os.path.isfile(result)


class TestThumbnailServiceFetch:
    @pytest.mark.asyncio
    async def test_fetch_thumbnail_downloads_and_caches(self):
        png_data = _make_test_png()
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = ThumbnailService(cache_dir=tmpdir)
            with patch("genlauncher_tui.services.image_service.httpx.AsyncClient") as MockClient:
                mock_resp = MockClient.return_value.__aenter__.return_value.get.return_value
                mock_resp.raise_for_status.return_value = None
                mock_resp.content = png_data
                path = await svc.fetch_thumbnail("https://example.com/img.png", "Test Mod")
                assert path is not None
                assert os.path.isfile(path)
                with open(path, "rb") as f:
                    assert f.read() == png_data

    @pytest.mark.asyncio
    async def test_fetch_thumbnail_uses_cache(self):
        png_data = _make_test_png()
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = ThumbnailService(cache_dir=tmpdir)
            cache_path = svc._cache_path("Test Mod")
            with open(cache_path, "wb") as f:
                f.write(png_data)
            # Should not call out to network
            with patch("genlauncher_tui.services.image_service.httpx.AsyncClient") as MockClient:
                path = await svc.fetch_thumbnail("https://example.com/img.png", "Test Mod")
                assert path == cache_path
                MockClient.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_thumbnail_returns_none_on_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            svc = ThumbnailService(cache_dir=tmpdir)
            with patch("genlauncher_tui.services.image_service.httpx.AsyncClient") as MockClient:
                mock_resp = MockClient.return_value.__aenter__.return_value.get.return_value
                mock_resp.raise_for_status.side_effect = Exception("HTTP error")
                path = await svc.fetch_thumbnail("https://example.com/bad.png", "Test Mod")
                assert path is None


class TestThumbnailServiceResize:
    def test_load_and_resize_preserves_aspect_ratio(self):
        png_data = _make_test_png(size=(200, 100))
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.png")
            with open(path, "wb") as f:
                f.write(png_data)
            result_bytes, w, h = ThumbnailService.load_and_resize(path)
            assert w <= 320
            assert h <= 100
            assert len(result_bytes) > 0
            assert result_bytes.startswith(b"\x89PNG")

    def test_load_and_resize_small_image(self):
        png_data = _make_test_png(size=(32, 24))
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "small.png")
            with open(path, "wb") as f:
                f.write(png_data)
            result_bytes, w, h = ThumbnailService.load_and_resize(path)
            assert w <= 320
            assert h <= 100
            assert len(result_bytes) > 0


class TestThumbnailServiceIntegration:
    def test_cache_dir_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "a", "b", "c")
            svc = ThumbnailService(cache_dir=nested)
            assert os.path.isdir(nested)
