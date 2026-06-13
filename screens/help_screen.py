from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class HelpScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss_help", "Close"),
    ]

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-dialog {
        width: 58;
        height: auto;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    #help-dialog Label {
        margin: 0 0;
    }

    #help-dialog .header {
        text-style: bold;
        color: $primary;
        padding-bottom: 1;
    }

    #help-dialog .section {
        text-style: bold;
        margin-top: 1;
    }

    #help-dialog .key-row {
        layout: horizontal;
        height: 1;
    }

    #help-dialog .key {
        width: 16;
        text-style: bold;
    }

    #help-dialog .desc {
        width: 1fr;
    }

    #help-dialog Button {
        dock: bottom;
        width: 100%;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Label("Keybindings & Usage", classes="header")

            yield Label("Navigation", classes="section")
            yield Static("")
            yield from self._row("a", "Browse available mods")
            yield from self._row("o", "Open options")
            yield from self._row("c", "View credits")
            yield from self._row("l", "Launch Zero Hour via Steam")
            yield from self._row("F1 / ?", "Show this help")
            yield from self._row("q", "Quit")
            yield from self._row("Esc", "Go back")

            yield Label("Mod Management", classes="section")
            yield Static("")
            yield from self._row("Tab / Click", "Select a mod row in the table")
            yield from self._row("Enter", "Open action menu for the selected mod")
            yield Static("")
            yield Label("Available actions on a mod:", classes="desc")
            yield Label("  Download   - Download mod files from the source")
            yield Label("  Install    - Install into the game directory")
            yield Label("  Uninstall  - Remove from game, restore originals")
            yield Label("  Delete     - Delete downloaded files (keep in list)")
            yield Label("  Remove     - Remove from your mod list entirely")

            yield Label("Install Methods (set in Options)", classes="section")
            yield Static("")
            yield Label("  Symlink  - Creates symlinks to mod files")
            yield Label("             (faster, no disk duplication)")
            yield Label("  Copy     - Copies mod files into game folder")
            yield Label("             (safe, uses more disk space)")

            yield Button("Close (Esc)", id="close-help-btn", variant="primary")

    def _row(self, key: str, desc: str):
        with Horizontal(classes="key-row"):
            yield Label(key, classes="key")
            yield Label(desc, classes="desc")

    def action_dismiss_help(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.action_dismiss_help()
