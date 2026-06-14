from __future__ import annotations

import base64
import io
import logging
import os

from rich.segment import Segment
from textual.strip import Strip
from textual.widget import Widget

try:
    from PIL import Image as PILImage
    from rich_pixels import Pixels

    _HAS_RICH_PIXELS = True
except ImportError:
    _HAS_RICH_PIXELS = False

logger = logging.getLogger(__name__)

_KITTY_CHECKS: list[tuple[str, callable]] = []
_ITERM2_CHECKS: list[tuple[str, callable]] = []


def _register_term(name: str, check_fn: callable, protocol: str = "kitty") -> None:
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
_register_term("wezterm", lambda: os.environ.get("TERM_PROGRAM") == "WezTerm", protocol="iterm2")


class ThumbnailWidget(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._png_data: bytes | None = None
        self._image_w: int = 0
        self._image_h: int = 0
        self._placeholder: str = ""
        self._kitty: bool = _supports_kitty()
        self._iterm2: bool = _supports_iterm2()
        self._fallback_strips: list[Strip] | None = None
        self._image_timer: Timer | None = None

    def on_unmount(self) -> None:
        self._stop_timer()

    def set_image(self, png_bytes: bytes | None, w: int = 0, h: int = 0, placeholder: str = "") -> None:
        self._png_data = png_bytes
        self._image_w = w
        self._image_h = h
        self._placeholder = placeholder
        self._fallback_strips = None
        self._update_image_display()
        self.refresh()

    def _update_image_display(self) -> None:
        if not self._png_data:
            self._stop_timer()
            return
        if self._kitty or self._iterm2:
            self._start_timer()
        else:
            self._stop_timer()
            if _HAS_RICH_PIXELS and self.size.width > 0:
                try:
                    self._render_fallback()
                except Exception:
                    logger.exception("Failed to render fallback thumbnail")
                    self._fallback_strips = []

    def _start_timer(self) -> None:
        if self._image_timer is None:
            self._image_timer = self.set_interval(0.05, self._write_image_to_terminal)

    def _stop_timer(self) -> None:
        if self._image_timer is not None:
            self._image_timer.stop()
            self._image_timer = None

    def _write_image_to_terminal(self) -> None:
        if not self._png_data or not (self._kitty or self._iterm2):
            return
        try:
            _ = self.app
        except Exception:
            return
        try:
            region = self.region
            if region.width == 0 or region.height == 0:
                return
            b64 = base64.b64encode(self._png_data).decode("ascii")
            pos = f"\x1b[{region.y + 1};{region.x + 1}H"

            if self._kitty:
                esc = (
                    f"\x1b7"
                    f"{pos}"
                    f"\x1b_Ga=T,f=100,s={self._image_w},v={self._image_h},m=0;{b64}\x1b\\"
                    f"\x1b8"
                )
            elif self._iterm2:
                esc = (
                    f"\x1b7"
                    f"{pos}"
                    f"\x1b]1337;File=inline=1;width=auto;height=auto:{b64}\x07"
                    f"\x1b8"
                )
            else:
                return

            self.app._driver.write(esc)
        except Exception:
            logger.exception("Failed to write image to terminal")

    def _render_fallback(self) -> None:
        if not self._png_data or not _HAS_RICH_PIXELS:
            self._fallback_strips = []
            return
        width = max(1, self.size.width)
        if width <= 0:
            self._fallback_strips = []
            return
        img = PILImage.open(io.BytesIO(self._png_data))
        img.thumbnail((width, self.size.height * 2), PILImage.LANCZOS)
        pixels = Pixels.from_image(img)

        from rich.console import Console
        console = Console(width=width, color_system="truecolor", force_terminal=True)
        options = console.options
        from rich.segment import Segments as RichSegments
        all_segments: list[Segment] = []
        for part in pixels.__rich_console__(console, options):
            if isinstance(part, str):
                all_segments.append(Segment(part))
            elif isinstance(part, RichSegments):
                all_segments.extend(part)
            else:
                all_segments.append(part)
        lines = Segment.split_lines(all_segments)
        self._fallback_strips = [Strip(list(line)) for line in lines]

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if not self._png_data:
            if y == 0:
                return Strip([Segment(self._placeholder.ljust(width))])
            return Strip([Segment(" " * width)])

        if self._kitty or self._iterm2:
            return Strip([Segment(" " * width)])

        if self._fallback_strips is None and _HAS_RICH_PIXELS:
            try:
                self._render_fallback()
            except Exception:
                logger.exception("Failed to render fallback thumbnail")
                self._fallback_strips = []
        if self._fallback_strips and y < len(self._fallback_strips):
            return self._fallback_strips[y]
        if y == 0:
            return Strip([Segment(self._placeholder.ljust(width))])
        return Strip([Segment(" " * width)])
