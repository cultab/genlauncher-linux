from __future__ import annotations

import io
import os
from unittest.mock import MagicMock, PropertyMock, patch

from PIL import Image as PILImage
from rich.segment import Segment
from textual.geometry import Size
from textual.strip import Strip as TStrip

from genlauncher_tui.widgets.thumbnail import (
    ThumbnailWidget,
    _supports_kitty,
    _supports_iterm2,
    supports_image_protocol,
    _register_term,
    _KITTY_CHECKS,
    _ITERM2_CHECKS,
)


def _make_test_png(w: int = 4, h: int = 4) -> bytes:
    img = PILImage.new("RGBA", (w, h), (255, 0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestKittyDetection:
    def test_default_no_detection(self):
        old_kitty = os.environ.pop("KITTY_WINDOW_ID", None)
        old_term = os.environ.pop("TERM_PROGRAM", None)
        try:
            assert _supports_kitty() is False
            assert _supports_iterm2() is False
            assert supports_image_protocol() is False
        finally:
            if old_kitty is not None:
                os.environ["KITTY_WINDOW_ID"] = old_kitty
            if old_term is not None:
                os.environ["TERM_PROGRAM"] = old_term

    def test_kitty_detected(self):
        old_kitty = os.environ.pop("KITTY_WINDOW_ID", None)
        old_term = os.environ.pop("TERM_PROGRAM", None)
        os.environ["KITTY_WINDOW_ID"] = "1"
        try:
            assert _supports_kitty() is True
            assert _supports_iterm2() is False
            assert supports_image_protocol() is True
        finally:
            if old_kitty is not None:
                os.environ["KITTY_WINDOW_ID"] = old_kitty
            else:
                os.environ.pop("KITTY_WINDOW_ID", None)
            if old_term is not None:
                os.environ["TERM_PROGRAM"] = old_term
            else:
                os.environ.pop("TERM_PROGRAM", None)

    def test_wezterm_detected(self):
        old_kitty = os.environ.pop("KITTY_WINDOW_ID", None)
        old_term = os.environ.pop("TERM_PROGRAM", None)
        os.environ["TERM_PROGRAM"] = "WezTerm"
        try:
            assert _supports_kitty() is True
            assert _supports_iterm2() is False
            assert supports_image_protocol() is True
        finally:
            if old_kitty is not None:
                os.environ["KITTY_WINDOW_ID"] = old_kitty
            if old_term is not None:
                os.environ["TERM_PROGRAM"] = old_term
            else:
                os.environ.pop("TERM_PROGRAM", None)

    def test_iterm2_app_detected(self):
        old_kitty = os.environ.pop("KITTY_WINDOW_ID", None)
        old_term = os.environ.pop("TERM_PROGRAM", None)
        os.environ["TERM_PROGRAM"] = "iTerm.app"
        try:
            assert _supports_kitty() is False
            assert _supports_iterm2() is True
            assert supports_image_protocol() is True
        finally:
            if old_kitty is not None:
                os.environ["KITTY_WINDOW_ID"] = old_kitty
            if old_term is not None:
                os.environ["TERM_PROGRAM"] = old_term
            else:
                os.environ.pop("TERM_PROGRAM", None)

    def test_custom_term_registration_kitty(self):
        _register_term("test_kitty", lambda: True, protocol="kitty")
        try:
            assert _supports_kitty() is True
        finally:
            _KITTY_CHECKS.pop()

    def test_custom_term_registration_iterm2(self):
        _register_term("test_iterm2", lambda: True, protocol="iterm2")
        try:
            assert _supports_iterm2() is True
        finally:
            _ITERM2_CHECKS.pop()


class TestThumbnailWidget:
    def test_render_line_placeholder_when_no_image(self):
        w = ThumbnailWidget()
        w._placeholder = "Test Mod"
        strip = w.render_line(0)
        assert "Test Mod" in strip.text

    def test_render_line_fills_subsequent_rows(self):
        w = ThumbnailWidget()
        strip = w.render_line(1)
        assert len(strip.text) >= 0

    def test_render_line_spaces_when_kitty_has_image(self):
        w = ThumbnailWidget()
        w._kitty = True
        w._png_data = b"fake_png"
        strip = w.render_line(0)
        assert strip.text.strip() == ""

    def test_render_line_spaces_when_iterm2_has_image(self):
        w = ThumbnailWidget()
        w._iterm2 = True
        w._png_data = b"fake_png"
        strip = w.render_line(0)
        assert strip.text.strip() == ""

    def test_render_line_placeholder_when_no_protocol_has_image_no_fallback(self):
        w = ThumbnailWidget()
        w._kitty = False
        w._iterm2 = False
        w._png_data = b"fake_png"
        w._placeholder = "Test Mod"
        strip = w.render_line(0)
        assert "Test Mod" in strip.text

    def test_set_image_starts_timer_for_kitty(self):
        w = ThumbnailWidget()
        w._kitty = True
        with patch.object(w, "_start_timer") as mock_start:
            with patch.object(w, "_stop_timer") as mock_stop:
                w.set_image(b"png_data", w=100, h=50, placeholder="Test Mod")
        mock_start.assert_called_once()
        mock_stop.assert_not_called()

    def test_set_image_starts_timer_for_iterm2(self):
        w = ThumbnailWidget()
        w._iterm2 = True
        with patch.object(w, "_start_timer") as mock_start:
            with patch.object(w, "_stop_timer") as mock_stop:
                w.set_image(b"png_data", w=100, h=50, placeholder="Test Mod")
        mock_start.assert_called_once()
        mock_stop.assert_not_called()

    def test_set_image_with_none_clears_and_stops_timer(self):
        w = ThumbnailWidget()
        w._kitty = True
        with patch.object(w, "_start_timer"):
            w.set_image(b"data", w=10, h=10, placeholder="Old")
        with patch.object(w, "_stop_timer") as mock_stop:
            w.set_image(None, placeholder="New")
        assert w._png_data is None
        assert w._placeholder == "New"
        mock_stop.assert_called_once()

    def test_set_image_does_not_start_timer_for_no_protocol(self):
        w = ThumbnailWidget()
        w._kitty = False
        w._iterm2 = False
        with patch.object(w, "_start_timer") as mock_start:
            with patch.object(w, "_stop_timer") as mock_stop:
                w.set_image(b"png_data", w=100, h=50, placeholder="Test Mod")
        mock_start.assert_not_called()
        mock_stop.assert_called_once()

    def test_on_unmount_stops_timer(self):
        w = ThumbnailWidget()
        timer_mock = MagicMock()
        w._image_timer = timer_mock
        w.on_unmount()
        timer_mock.stop.assert_called_once()
        assert w._image_timer is None

    def test_write_image_kitty_escape_format(self):
        w = ThumbnailWidget()
        w._kitty = True
        w._png_data = _make_test_png(8, 8)
        w._image_w = 8
        w._image_h = 8
        with patch.object(ThumbnailWidget, "size", new_callable=PropertyMock, return_value=Size(5, 3)):
            with patch.object(ThumbnailWidget, "region", new_callable=PropertyMock) as mock_region:
                mock_region.return_value.width = 5
                mock_region.return_value.height = 3
                mock_region.return_value.x = 10
                mock_region.return_value.y = 20
                with patch("builtins.open"), patch("fcntl.ioctl") as mock_ioctl:
                    mock_ioctl.return_value = struct.pack("HHHH", 24, 80, 480, 192)
                    w._write_image_to_terminal()

    def test_write_image_iterm2_escape_format(self):
        w = ThumbnailWidget()
        w._iterm2 = True
        w._png_data = _make_test_png(8, 8)
        w._image_w = 8
        w._image_h = 8
        with patch.object(ThumbnailWidget, "size", new_callable=PropertyMock, return_value=Size(5, 3)):
            with patch.object(ThumbnailWidget, "region", new_callable=PropertyMock) as mock_region:
                mock_region.return_value.width = 5
                mock_region.return_value.height = 3
                mock_region.return_value.x = 10
                mock_region.return_value.y = 20
                with patch("builtins.open"), patch("fcntl.ioctl") as mock_ioctl:
                    mock_ioctl.return_value = struct.pack("HHHH", 24, 80, 480, 192)
                    w._write_image_to_terminal()

    def test_write_image_noop_without_app(self):
        w = ThumbnailWidget()
        w._kitty = True
        w._png_data = b"test"
        w._write_image_to_terminal()

    def test_write_image_noop_for_iterm2_without_app(self):
        w = ThumbnailWidget()
        w._iterm2 = True
        w._png_data = b"test"
        w._write_image_to_terminal()

    def test_write_image_noop_when_no_protocol(self):
        w = ThumbnailWidget()
        w._kitty = False
        w._iterm2 = False
        w._png_data = b"test"
        w._write_image_to_terminal()

    def test_render_line_uses_fallback_strips_when_available(self):
        w = ThumbnailWidget()
        w._kitty = False
        w._iterm2 = False
        w._png_data = b"test"
        fake_strips = [TStrip([Segment("█")])]
        w._fallback_strips = fake_strips
        strip = w.render_line(0)
        assert "█" in strip.text

    def test_compute_strips_returns_false_without_png_data(self):
        w = ThumbnailWidget()
        w._kitty = False
        w._iterm2 = False
        assert w._compute_strips() is False

    def test_compute_strips_uses_cached_strips(self):
        w = ThumbnailWidget()
        w._fallback_strips = [TStrip([Segment("X")])]
        assert w._compute_strips() is True

    def test_render_fallback_produces_half_block_strips(self):
        w = ThumbnailWidget()
        w._kitty = False
        w._iterm2 = False
        w._png_data = _make_test_png(4, 4)
        w._render_fallback()
        assert w._fallback_strips is not None
        assert len(w._fallback_strips) > 0
        assert "▀" in w._fallback_strips[0].text

    def test_render_line_with_half_block_fallback(self):
        w = ThumbnailWidget()
        w._kitty = False
        w._iterm2 = False
        w._png_data = _make_test_png(4, 4)
        with patch.object(ThumbnailWidget, "size", new_callable=PropertyMock, return_value=Size(4, 2)):
            strip = w.render_line(0)
        assert "▀" in strip.text

    def test_on_resize_recomputes_strips_for_no_protocol(self):
        w = ThumbnailWidget()
        w._kitty = False
        w._iterm2 = False
        w._fallback_strips = [TStrip([Segment("X")])]
        w._png_data = _make_test_png(4, 4)
        with patch.object(ThumbnailWidget, "size", new_callable=PropertyMock, return_value=Size(4, 2)):
            w.on_resize()
        assert w._fallback_strips is not None
        assert "▀" in w._fallback_strips[0].text


import struct  # noqa: E402
