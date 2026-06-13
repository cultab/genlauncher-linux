from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label, Static

if TYPE_CHECKING:
    from genlauncher_tui.screens.home_screen import HomeScreen


class KeyHints(Static):
    def __init__(self, screen: HomeScreen, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._screen = screen

    def compose(self) -> ComposeResult:
        yield Label("Keys", classes="section-header")
        yield from self._row("a", "Add Mods")
        yield from self._row("o", "Options")
        yield from self._row("c", "Credits")
        yield from self._row("l", "Launch Game")
        yield from self._row("q", "Quit")
        yield from self._row("F1 / ?", "Help")
        yield from self._row("Esc", "Home")

    def _row(self, key: str, desc: str):
        with Horizontal(classes="key-row"):
            yield Label(key, classes="key")
            yield Label(desc, classes="desc")
