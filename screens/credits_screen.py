from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Header, Footer


class CreditsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="credits-content"):
            yield Label("GenLauncher TUI", id="credits-title")
            yield Label("A Zero Hour Mod Manager")
            yield Label("")
            yield Label("Original GenLauncher by Pal_Ser")
            yield Label("Original GenLauncherWeb by Tricky!")
            yield Label("Python TUI port using Textual")
            yield Label("")
            yield Label("Special thanks:")
            yield Label("  - Sebi (testing and feedback)")
            yield Label("  - Textualize (Textual framework)")
            yield Label("  - The C&C Generals modding community")
            yield Label("")
        yield Button("Back", id="back-btn", variant="default")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
