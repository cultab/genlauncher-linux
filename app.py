from __future__ import annotations

from textual.app import App
from textual.binding import Binding

from genlauncher_tui.screens.home_screen import HomeScreen
from genlauncher_tui.screens.add_mod_screen import AddModScreen
from genlauncher_tui.screens.options_screen import OptionsScreen
from genlauncher_tui.screens.credits_screen import CreditsScreen
from genlauncher_tui.services.mod_service import ModService
from genlauncher_tui.services.options_service import OptionsService
from genlauncher_tui.services.repo_service import RepoService


class GenLauncherApp(App):
    CSS = """
    Screen {
        background: $surface;
    }

    DataTable {
        height: 1fr;
        margin: 0 1;
    }

    DataTable > .datatable--header {
        background: $primary 30%;
        color: $text;
        text-style: bold;
    }

    Button {
        margin: 1 1;
    }

    .action-panel {
        width: 30;
        min-width: 26;
        padding: 1 1;
        border-left: solid $primary;
    }

    .action-panel Button {
        width: 100%;
    }

    .status-row {
        height: 3;
        padding: 0 1;
    }

    .status-label {
        width: 20;
    }

    .status-value {
        width: 1fr;
    }

    .ok {
        color: $success;
    }
    .fail {
        color: $error;
    }

    #hint-text {
        height: 1;
        dock: bottom;
        width: 1fr;
        color: $text-muted;
        text-style: italic;
        padding: 0 1;
    }

    #mod-actions {
        display: none;
        margin: 1 0;
        padding: 0 1;
    }

    #mod-actions Button {
        width: 100%;
        margin: 0 0 1 0;
    }

    #mod-list {
        height: 1fr;
    }

    #back-button {
        dock: bottom;
        width: 100%;
    }

    .main-container {
        layout: horizontal;
        height: 1fr;
    }

    .left-panel {
        width: 1fr;
        padding: 1 1;
    }

    .right-panel {
        width: 34;
        min-width: 30;
        padding: 1 1;
        border-left: solid $primary;
    }

    OptionsScreen Input {
        width: 1fr;
    }

    OptionsScreen RadioSet {
        margin: 1 0;
    }

    #credits-content {
        padding: 2 4;
    }

    #credits-content Label {
        margin: 1 0;
    }

    .download-progress {
        margin: 1 1;
    }
    """

    TITLE = "GenLauncher TUI"
    SUB_TITLE = "Zero Hour Mod Manager"

    BINDINGS = [
        Binding("a", "go_add_mod", "Add Mod"),
        Binding("o", "go_options", "Options"),
        Binding("c", "go_credits", "Credits"),
        Binding("l", "launch_game", "Launch Game"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "go_home", "Home"),
    ]

    SCREENS = {
        "home": HomeScreen,
        "add_mod": AddModScreen,
        "options": OptionsScreen,
        "credits": CreditsScreen,
    }

    def __init__(self):
        super().__init__()
        self.mod_service = ModService()
        self.options_service = OptionsService()
        self.repo_service = RepoService()

    def on_mount(self) -> None:
        self.push_screen("home")

    def action_go_add_mod(self) -> None:
        self.push_screen("add_mod")

    def action_go_options(self) -> None:
        self.push_screen("options")

    def action_go_credits(self) -> None:
        self.push_screen("credits")

    def action_go_home(self) -> None:
        self.pop_screen()

    def action_launch_game(self) -> None:
        import webbrowser
        webbrowser.open("steam://rungameid/2732960")
