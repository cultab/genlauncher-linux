from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Input, RadioSet, RadioButton, Header, Footer

from genlauncher_tui.models.enums import InstallMethod
from genlauncher_tui.models.options import LauncherOptions

if TYPE_CHECKING:
    from genlauncher_tui.app import GenLauncherApp


class OptionsScreen(Screen):
    @property
    def app(self) -> GenLauncherApp:
        return super().app  # type: ignore[return-value]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Label("Options", id="options-title")
            yield Label("Install Method:")
            yield RadioSet(
                RadioButton("Symlink (recommended)", id="symlink-opt"),
                RadioButton("Copy files", id="copy-opt"),
                id="install-method-set",
            )
            yield Label("")
            yield Label("Steam Path:")
            yield Input(id="steam-path-input", placeholder="Path to Steam common folder")
            yield Label("")
            with Vertical():
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Reset to Defaults", id="reset-btn")
                yield Button("Back", id="back-btn", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        self._load_options()

    def _load_options(self):
        opts = self.app.options_service.get_options()
        radio_set = self.query_one("#install-method-set", RadioSet)
        steam_input = self.query_one("#steam-path-input", Input)
        steam_input.value = opts.steam_path
        if opts.install_method == InstallMethod.SymLink:
            radio_set.index = 0  # type: ignore[attr-defined]
        else:
            radio_set.index = 1  # type: ignore[attr-defined]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save_options()
        elif event.button.id == "reset-btn":
            self.app.options_service.reset_options()
            self._load_options()
            self.notify("Options reset to defaults", severity="information")
        elif event.button.id == "back-btn":
            self.app.pop_screen()

    def _save_options(self):
        radio_set = self.query_one("#install-method-set", RadioSet)
        steam_input = self.query_one("#steam-path-input", Input)
        method = InstallMethod.SymLink if radio_set.index == 0 else InstallMethod.CopyFiles  # type: ignore[attr-defined]
        opts = LauncherOptions(
            install_method=method,
            steam_path=steam_input.value.strip(),
        )
        self.app.options_service.set_options(opts)
        self.notify("Options saved", severity="information")
