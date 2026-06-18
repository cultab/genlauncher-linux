from __future__ import annotations

import logging
import os

from textual.app import ComposeResult
from textual.widgets import Button, Label, Static

from genlauncher_tui.models.options import InstallationStatus
from genlauncher_tui.services.steam_service import SteamService


logger = logging.getLogger(__name__)


class StatusPanel(Static):
    def compose(self) -> ComposeResult:
        yield Label("Status", classes="section-header")
        yield Label("", id="gen-tool-status")
        yield Label("", id="modded-launcher-status")
        yield Label("", id="steam-path-label")
        yield Button("Install GenTool", id="install-gentool-btn", variant="primary")

    def refresh_status(self, status: InstallationStatus) -> None:
        gt = self.query_one("#gen-tool-status", Label)
        ml = self.query_one("#modded-launcher-status", Label)
        sp = self.query_one("#steam-path-label", Label)
        gt.update(f"GenTool: {'[green]● Installed[/]' if status.gen_tool else '[red]● Not installed[/]'}")
        ml.update(f"Modded Launcher: {'[green]● Installed[/]' if status.modded_launcher else '[red]● Not installed[/]'}")
        btn = self.query_one("#install-gentool-btn", Button)
        btn.display = not status.gen_tool
        try:
            path = SteamService.get_game_install_dir()
            home = os.path.expanduser("~")
            display = path.replace(home, "~", 1)
            sp.update(f"Game: {display}")
        except Exception:
            logger.warning("Could not determine game install path", exc_info=True)
            sp.update("[red]Game: Not found[/]")
