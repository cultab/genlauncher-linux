from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import DataTable, Label, Button, Header, Footer, Static

from genlauncher_tui.models.enums import InstallMethod
from genlauncher_tui.models.mod import Mod, standard_mod_name
from genlauncher_tui.models.options import InstallationStatus
from genlauncher_tui.services.steam_service import SteamService


class HomeScreen(Screen):
    BINDINGS = [
        Binding("f1", "show_help", "Help"),
        Binding("?", "show_help", "Help"),
    ]

    added_mods: reactive[list[Mod]] = reactive([])
    install_status: reactive[InstallationStatus] = reactive(InstallationStatus())

    def __init__(self):
        super().__init__()
        self._poll_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        app = self.app
        with Horizontal():
            with Vertical(classes="left-panel"):
                yield DataTable(id="mod-table", cursor_type="row")
                yield Label("Select a mod row and press Enter for actions", id="hint-text", classes="status-label")
            with Vertical(classes="right-panel"):
                yield Label("Actions", classes="status-label")
                yield Button("Launch Game", id="launch-btn", variant="primary")
                yield Button("Add Mods", id="add-mod-btn")
                yield Button("Options", id="options-btn")
                yield Button("Help (F1)", id="help-btn")
                yield Button("Credits", id="credits-btn")
                yield Button("Exit", id="exit-btn", variant="error")
                yield Static("", classes="status-row")
                yield Label("Status", classes="status-label")
                yield Label("", id="gen-tool-status")
                yield Label("", id="modded-launcher-status")
                yield Label("", id="steam-path-label", classes="status-label")

    def on_mount(self) -> None:
        table = self.query_one("#mod-table", DataTable)
        table.columns.clear()
        table.add_column("Mod", width=30)
        table.add_column("Version", width=12)
        table.add_column("Status", width=14)
        table.add_column("Size", width=10)
        self._refresh_mods()
        self._refresh_status()
        self._poll_task = self.set_interval(2.0, self._poll_status)

    def on_screen_resume(self) -> None:
        self._refresh_mods()
        self._refresh_status()

    def refresh_data(self) -> None:
        self._refresh_mods()
        self._refresh_status()

    def _refresh_mods(self):
        app = self.app
        mods = app.mod_service.get_added_mods()
        self.added_mods = mods
        table = self.query_one("#mod-table", DataTable)
        hint = self.query_one("#hint-text", Label)
        table.clear()
        if mods:
            hint.update("Select a mod and press Enter to Download / Install / Uninstall")
        else:
            hint.update("Add mods first — press a or click 'Add Mods'")
        for mod in mods:
            name = mod.mod_info.mod_name if mod.mod_info else "?"
            ver = mod.downloaded_version or "-"
            if mod.installed:
                status = "Installed"
            elif mod.downloading:
                status = "Downloading..."
            elif mod.downloaded:
                status = "Downloaded"
            else:
                status = "Not downloaded"
            size_str = _format_size(mod.total_size)
            table.add_row(name, ver, status, size_str)

    def _refresh_status(self):
        app = self.app
        self.install_status = app.mod_service.get_installation_status()
        gt = self.query_one("#gen-tool-status", Label)
        ml = self.query_one("#modded-launcher-status", Label)
        sp = self.query_one("#steam-path-label", Label)
        status = self.install_status
        gt.update(f"GenTool: {'[green]OK[/]' if status.gen_tool else '[red]Not installed[/]'}")
        ml.update(f"Modded Launcher: {'[green]OK[/]' if status.modded_launcher else '[red]Not installed[/]'}")
        try:
            path = SteamService.get_game_install_dir()
            sp.update(f"Game: {path}")
        except Exception:
            sp.update("Game: Not found")

    def _poll_status(self) -> None:
        self._refresh_status()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#mod-table", DataTable)
        row_key = event.row_key
        if row_key is None:
            return
        rows = table.rows
        if row_key not in rows:
            return
        idx = list(rows.keys()).index(row_key)
        if idx < len(self.added_mods):
            self._show_mod_actions(idx)

    def _show_mod_actions(self, idx: int):
        mod = self.added_mods[idx]

        def action(label: str, action_fn):
            async def handler():
                try:
                    action_fn()
                except Exception as e:
                    from textual import log
                    log.error(str(e))
                    self.notify(str(e), severity="error")
                self._refresh_mods()

        buttons = []
        if not mod.downloaded and not mod.installed:
            buttons.append(("Download", self._do_download(mod)))
        if mod.downloaded and not mod.installed:
            buttons.append(("Install", self._do_install(mod)))
        if mod.installed:
            buttons.append(("Uninstall", self._do_uninstall(mod)))
        if mod.downloaded and not mod.installed:
            buttons.append(("Delete Files", self._do_delete(mod)))
        if not mod.installed:
            buttons.append(("Remove from List", self._do_remove(mod)))

        if not buttons:
            return

        from textual.screen import ModalScreen
        from textual.widgets import Button as Btn
        from textual.containers import Vertical as V

        class ModActions(ModalScreen):
            def compose(self):
                with V():
                    yield Label(f"Actions for: {mod.mod_info.mod_name if mod.mod_info else '?'}")
                    for label, _cb in buttons:
                        yield Btn(label, id=f"act-{label.lower().replace(' ', '-')}")

            def on_button_pressed(self, event: Btn.Pressed):
                for label, cb in buttons:
                    if event.button.id == f"act-{label.lower().replace(' ', '-')}":
                        self.dismiss(cb)
                        return

        def on_done(cb):
            if cb:
                asyncio.ensure_future(cb)

        self.app.push_screen(ModActions(), on_done)

    async def _do_download(self, mod: Mod):
        name = mod.mod_info.mod_name
        self.notify(f"Downloading {name}...", timeout=2)
        try:
            await self.app.mod_service.download_mod(name)
            self.notify(f"{name} downloaded", severity="information")
        except Exception as e:
            self.notify(f"Download failed: {e}", severity="error")
        self._refresh_mods()

    def _do_install(self, mod: Mod):
        name = mod.mod_info.mod_name
        opts = self.app.options_service.get_options()
        try:
            self.app.mod_service.install_mod(name, opts.install_method)
            self.notify(f"{name} installed", severity="information")
        except Exception as e:
            self.notify(f"Install failed: {e}", severity="error")
        self._refresh_mods()

    def _do_uninstall(self, mod: Mod):
        name = mod.mod_info.mod_name
        try:
            self.app.mod_service.uninstall_mod(name)
            self.notify(f"{name} uninstalled", severity="information")
        except Exception as e:
            self.notify(f"Uninstall failed: {e}", severity="error")
        self._refresh_mods()

    def _do_delete(self, mod: Mod):
        name = mod.mod_info.mod_name
        try:
            self.app.mod_service.delete_mod(name)
            self.notify(f"{name} files deleted", severity="information")
        except Exception as e:
            self.notify(f"Delete failed: {e}", severity="error")
        self._refresh_mods()

    def _do_remove(self, mod: Mod):
        name = mod.mod_info.mod_name
        try:
            self.app.mod_service.remove_mod_from_list(name)
            self.notify(f"{name} removed", severity="information")
        except Exception as e:
            self.notify(f"Remove failed: {e}", severity="error")
        self._refresh_mods()

    def action_show_help(self) -> None:
        from genlauncher_tui.screens.help_screen import HelpScreen
        self.app.push_screen(HelpScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch-btn":
            import webbrowser
            webbrowser.open("steam://rungameid/2732960")
        elif event.button.id == "add-mod-btn":
            self.app.action_go_add_mod()
        elif event.button.id == "options-btn":
            self.app.action_go_options()
        elif event.button.id == "help-btn":
            self.action_show_help()
        elif event.button.id == "credits-btn":
            self.app.action_go_credits()
        elif event.button.id == "exit-btn":
            self.app.exit()


def _format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "-"
    mb = size_bytes / (1024 * 1024)
    if mb < 1024:
        return f"{mb:.0f} MB"
    gb = mb / 1024
    return f"{gb:.1f} GB"
