from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Label

from genlauncher_tui.models.mod import Mod


class ModActionPanel(Vertical):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mod: Mod | None = None

    def compose(self) -> ComposeResult:
        yield Label(id="action-mod-name")
        yield Button("Download", id="act-download", variant="primary")
        yield Button("Install", id="act-install", variant="primary")
        yield Button("Uninstall", id="act-uninstall", variant="default")
        yield Button("Delete Files", id="act-delete", variant="warning")
        yield Button("Remove", id="act-remove", variant="error")

    def show_for_mod(self, mod: Mod | None) -> None:
        self._mod = mod
        if mod is None:
            self.display = False
            return
        self.display = True
        name = mod.mod_info.mod_name if mod.mod_info else "?"
        self.query_one("#action-mod-name", Label).update(f"[b]{name}[/]")
        self.query_one("#act-download", Button).display = not mod.downloaded and not mod.installed
        self.query_one("#act-install", Button).display = mod.downloaded and not mod.installed
        self.query_one("#act-uninstall", Button).display = mod.installed
        self.query_one("#act-delete", Button).display = mod.downloaded and not mod.installed
        self.query_one("#act-remove", Button).display = not mod.installed
