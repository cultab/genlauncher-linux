from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Label

from genlauncher_tui.models.mod import Mod
from genlauncher_tui.widgets.thumbnail_cell import ThumbnailCell


def _format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "-"
    mb = size_bytes / (1024 * 1024)
    if mb < 1024:
        return f"{mb:.0f} MB"
    gb = mb / 1024
    return f"{gb:.1f} GB"


class ModRow(Horizontal):
    def __init__(self, mod: Mod, index: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mod = mod
        self._index = index
        self._thumb: ThumbnailCell | None = None

    def compose(self) -> ComposeResult:
        mod = self._mod
        name = mod.mod_info.mod_name if mod.mod_info else "?"
        ver = str(mod.downloaded_version or "-")
        if mod.installed:
            status = "[green]Installed[/]"
        elif mod.downloading:
            status = "[yellow]Downloading...[/]"
        elif mod.downloaded:
            status = "[yellow]Downloaded[/]"
        else:
            status = "[grey]Not downloaded[/]"
        size_str = _format_size(mod.total_size)

        self._thumb = ThumbnailCell(placeholder=name, classes="row-thumbnail", id=f"thumb-{self._index}")
        yield self._thumb
        yield Label(name, classes="row-name", id=f"name-{self._index}")
        yield Label(ver, classes="row-version", id=f"ver-{self._index}")
        yield Label(status, classes="row-status", id=f"status-{self._index}")
        yield Label(size_str, classes="row-size", id=f"size-{self._index}")
        with Horizontal(classes="row-buttons"):
            yield Button("Download", id=f"dl-{self._index}", classes="row-btn")
            yield Button("Install", id=f"inst-{self._index}", classes="row-btn")
            yield Button("Uninstall", id=f"uninst-{self._index}", classes="row-btn")
            yield Button("Delete", id=f"del-{self._index}", classes="row-btn")
            yield Button("Remove", id=f"rem-{self._index}", classes="row-btn")

    def on_mount(self) -> None:
        self._set_button_visibility()

    def _set_button_visibility(self) -> None:
        mod = self._mod
        self.query_one(f"#dl-{self._index}", Button).display = not mod.downloaded and not mod.installed
        self.query_one(f"#inst-{self._index}", Button).display = mod.downloaded and not mod.installed
        self.query_one(f"#uninst-{self._index}", Button).display = mod.installed
        self.query_one(f"#del-{self._index}", Button).display = mod.downloaded and not mod.installed
        self.query_one(f"#rem-{self._index}", Button).display = not mod.installed

    def refresh_for_mod(self, mod: Mod) -> None:
        self._mod = mod
        name = mod.mod_info.mod_name if mod.mod_info else "?"
        self.query_one(f"#name-{self._index}", Label).update(name)
        ver = str(mod.downloaded_version or "-")
        self.query_one(f"#ver-{self._index}", Label).update(ver)
        if mod.installed:
            status = "[green]Installed[/]"
        elif mod.downloading:
            status = "[yellow]Downloading...[/]"
        elif mod.downloaded:
            status = "[yellow]Downloaded[/]"
        else:
            status = "[grey]Not downloaded[/]"
        self.query_one(f"#status-{self._index}", Label).update(status)
        size_str = _format_size(mod.total_size)
        self.query_one(f"#size-{self._index}", Label).update(size_str)
        self._set_button_visibility()

    @property
    def thumbnail_cell(self) -> Optional[ThumbnailCell]:
        return self._thumb

    def mod(self) -> Mod:
        return self._mod

    def mod_index(self) -> int:
        return self._index
