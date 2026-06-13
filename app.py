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
    CSS_PATH = "styles/app.tcss"

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
