from __future__ import annotations

import io
import logging

from PIL import Image as PILImage
from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widget import Widget

logger = logging.getLogger(__name__)

# Half-block characters for pixel rendering
_HALF_BLOCK = "▀"
_SPACE = " "


class ThumbnailCell(Widget):
    def __init__(self, placeholder: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._png_data: bytes | None = None
        self._fallback_strips: list[Strip] | None = None
        self._placeholder: str = placeholder

    def set_image(self, png_bytes: bytes | None, w: int = 0, h: int = 0, placeholder: str = "") -> None:
        self._png_data = png_bytes
        if placeholder:
            self._placeholder = placeholder
        self._fallback_strips = None
        if self.size.width >= 1 and self.size.height >= 1:
            self._compute_strips()
        self.refresh()

    def on_resize(self) -> None:
        if self._png_data:
            self._fallback_strips = None
            self._compute_strips()
            self.refresh()

    def _compute_strips(self) -> bool:
        if self._fallback_strips is not None:
            return True
        if not self._png_data or self.size.width < 1 or self.size.height < 1:
            return False
        try:
            self._render_fallback()
        except Exception:
            logger.exception("Failed to render inline thumbnail")
            self._fallback_strips = []
        return bool(self._fallback_strips)

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if not self._png_data:
            if y == 0:
                display = self._placeholder
                if len(display) > width:
                    display = display[:width]
                return Strip([Segment(display.ljust(width))])
            return Strip([Segment(_SPACE * width)])

        self._compute_strips()
        strips = self._fallback_strips
        if strips and y < len(strips):
            return strips[y]
        if y == 0:
            display = self._placeholder
            if len(display) > width:
                display = display[:width]
            return Strip([Segment(display.ljust(width))])
        return Strip([Segment(_SPACE * width)])

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
