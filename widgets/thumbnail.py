from __future__ import annotations

import base64
import fcntl
import io
import logging
import os
import struct
import sys
import termios
from typing import Callable

from PIL import Image as PILImage
from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.timer import Timer
from textual.widget import Widget

logger = logging.getLogger(__name__)

_HALF_BLOCK = "▀"
_SPACE = " "

_KITTY_CHECKS: list[tuple[str, Callable[[], bool]]] = []
_ITERM2_CHECKS: list[tuple[str, Callable[[], bool]]] = []

_FONT_CELL_W: int = 0
_FONT_CELL_H: int = 0


def _register_term(name: str, check_fn: Callable[[], bool], protocol: str = "kitty") -> None:
    if protocol == "kitty":
        _KITTY_CHECKS.append((name, check_fn))
    elif protocol == "iterm2":
        _ITERM2_CHECKS.append((name, check_fn))


def _supports_kitty() -> bool:
    return any(fn() for _, fn in _KITTY_CHECKS)


def _supports_iterm2() -> bool:
    return any(fn() for _, fn in _ITERM2_CHECKS)


def supports_image_protocol() -> bool:
    return _supports_kitty() or _supports_iterm2()


_register_term("kitty", lambda: bool(os.environ.get("KITTY_WINDOW_ID")), protocol="kitty")
_register_term("wezterm", lambda: os.environ.get("TERM_PROGRAM") == "WezTerm", protocol="kitty")
_register_term("iterm2", lambda: os.environ.get("TERM_PROGRAM") == "iTerm.app", protocol="iterm2")


def _get_font_cell_size() -> tuple[int, int]:
    global _FONT_CELL_W, _FONT_CELL_H
    if _FONT_CELL_W > 0 and _FONT_CELL_H > 0:
        return _FONT_CELL_W, _FONT_CELL_H
    try:
        s = struct.pack("HHHH", 0, 0, 0, 0)
        result = fcntl.ioctl(1, termios.TIOCGWINSZ, s)
        _rows, _cols, xpix, ypix = struct.unpack("HHHH", result)
        if xpix > 0 and ypix > 0 and _cols > 0 and _rows > 0:
            _FONT_CELL_W = xpix // _cols
            _FONT_CELL_H = ypix // _rows
    except Exception:
        pass
    if _FONT_CELL_W == 0:
        _FONT_CELL_W = 10
    if _FONT_CELL_H == 0:
        _FONT_CELL_H = 20
    return _FONT_CELL_W, _FONT_CELL_H


class ThumbnailWidget(Widget):
    _next_image_id: int = 0

    def __init__(self, placeholder: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image_id = ThumbnailWidget._next_image_id
        ThumbnailWidget._next_image_id += 1
        self._png_data: bytes | None = None
        self._image_w: int = 0
        self._image_h: int = 0
        self._placeholder: str = placeholder
        self._kitty: bool = _supports_kitty()
        self._iterm2: bool = _supports_iterm2()
        self._fallback_strips: list[Strip] | None = None
        self._image_timer: Timer | None = None
        self._transmitted: bool = False

    def on_unmount(self) -> None:
        self._stop_timer()

    def set_image(self, png_bytes: bytes | None, w: int = 0, h: int = 0, placeholder: str = "") -> None:
        self._png_data = png_bytes
        self._image_w = w
        self._image_h = h
        if placeholder:
            self._placeholder = placeholder
        self._fallback_strips = None
        self._transmitted = False
        self._update_image_display()
        self.refresh()

    def on_resize(self) -> None:
        if self._png_data and not (self._kitty or self._iterm2):
            self._fallback_strips = None
            self._compute_strips()
            self.refresh()

    def _update_image_display(self) -> None:
        if not self._png_data:
            self._stop_timer()
            return
        if self._kitty or self._iterm2:
            self._start_timer()
        else:
            self._stop_timer()
            if self.size.width >= 1 and self.size.height >= 1:
                self._compute_strips()

    def _start_timer(self) -> None:
        if self._image_timer is None:
            self._image_timer = self.set_interval(0.08, self._write_image_to_terminal)

    def _stop_timer(self) -> None:
        if self._image_timer is not None:
            self._image_timer.stop()
            self._image_timer = None

    def _write_image_to_terminal(self) -> None:
        if not self._png_data or not (self._kitty or self._iterm2):
            return
        try:
            region = self.region
            cells_w = self.size.width
            cells_h = self.size.height
            if region.width == 0 or region.height == 0 or cells_w == 0 or cells_h == 0:
                return
            b64 = base64.b64encode(self._png_data).decode("ascii")
            pos = f"\x1b[{region.y + 1};{region.x + 1}H"

            if self._kitty:
                cell_w_px, cell_h_px = _get_font_cell_size()
                pixel_w = cells_w * cell_w_px
                pixel_h = cells_h * cell_h_px
                if not self._transmitted:
                    # Transmit once — stores image in kitty's memory
                    esc = (
                        f"\x1b7"
                        f"{pos}"
                        f"\x1b_Ga=T,i={self._image_id},f=100,s={self._image_w},v={self._image_h},m=0;{b64}\x1b\\"
                        f"\x1b8"
                    )
                    self._transmitted = True
                else:
                    # Subsequent ticks only place (no heavy base64 transmit)
                    esc = (
                        f"\x1b7"
                        f"{pos}"
                        f"\x1b_Ga=p,i={self._image_id},w={pixel_w},h={pixel_h}\x1b\\"
                        f"\x1b8"
                    )
            elif self._iterm2:
                cell_w_px, _ = _get_font_cell_size()
                pixel_w = cells_w * cell_w_px
                esc = (
                    f"\x1b7"
                    f"{pos}"
                    f"\x1b]1337;File=inline=1;width={pixel_w}px;preserveAspectRatio=1:{b64}\x07"
                    f"\x1b8"
                )
            else:
                return

            os.write(1, esc.encode("ascii"))
        except Exception:
            logger.exception("Failed to write image to terminal")

    def _compute_strips(self) -> bool:
        if self._fallback_strips is not None:
            return True
        if not self._png_data or self.size.width < 1 or self.size.height < 1:
            return False
        try:
            self._render_fallback()
        except Exception:
            logger.exception("Failed to render half-block thumbnail")
            self._fallback_strips = []
        return bool(self._fallback_strips)

    def _render_fallback(self) -> None:
        if not self._png_data:
            self._fallback_strips = []
            return
        cell_w = max(1, self.size.width)
        cell_h = max(1, self.size.height)
        img = PILImage.open(io.BytesIO(self._png_data))
        img = img.convert("RGBA")
        img = img.resize((cell_w, cell_h * 2), PILImage.LANCZOS)

        strips: list[Strip] = []
        for row in range(cell_h):
            segments: list[Segment] = []
            for col in range(cell_w):
                top_pixel = img.getpixel((col, row * 2))
                bot_row = min(row * 2 + 1, img.height - 1)
                bottom_pixel = img.getpixel((col, bot_row))
                top_r, top_g, top_b, top_a = top_pixel
                bot_r, bot_g, bot_b, bot_a = bottom_pixel
                top_col = Style.parse(f"rgb({top_r},{top_g},{top_b})").color if top_a >= 128 else None
                bot_col = Style.parse(f"rgb({bot_r},{bot_g},{bot_b})").color if bot_a >= 128 else None
                seg = Segment(_HALF_BLOCK, Style(color=top_col, bgcolor=bot_col))
                segments.append(seg)
            strips.append(Strip(segments))
        self._fallback_strips = strips

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if not self._png_data:
            if y == 0:
                display = self._placeholder
                if width > 0 and len(display) > width:
                    display = display[:width]
                return Strip([Segment(display.ljust(width))])
            return Strip([Segment(_SPACE * width)])

        if self._kitty or self._iterm2:
            return Strip([Segment(_SPACE * width)])

        self._compute_strips()
        strips = self._fallback_strips
        if strips and y < len(strips):
            return strips[y]
        if y == 0:
            display = self._placeholder
            if width > 0 and len(display) > width:
                display = display[:width]
            return Strip([Segment(display.ljust(width))])
        return Strip([Segment(_SPACE * width)])
