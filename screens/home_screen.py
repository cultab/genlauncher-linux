from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import DataTable, Label, Button, ProgressBar, Static

from genlauncher_tui.models.mod import Mod
from genlauncher_tui.models.options import InstallationStatus
from genlauncher_tui.services.image_service import ThumbnailService
from genlauncher_tui.services.steam_service import SteamService
from genlauncher_tui.widgets.action_panel import ModActionPanel
from genlauncher_tui.widgets.key_hints import KeyHints
from genlauncher_tui.widgets.status_panel import StatusPanel
from genlauncher_tui.widgets.thumbnail import ThumbnailWidget, supports_image_protocol


logger = logging.getLogger(__name__)


class HomeScreen(Screen):
    @property
    def app(self) -> App:
        return super().app

    BINDINGS = [
        Binding("f1", "show_help", "Help"),
        Binding("?", "show_help", "Help"),
    ]

    added_mods: reactive[list[Mod]] = reactive([])
    install_status: reactive[InstallationStatus] = reactive(InstallationStatus())
    selected_mod: reactive[Mod | None] = reactive(None)

    def __init__(self):
        super().__init__()
        self._poll_task: Timer | None = None
        self._image_service: ThumbnailService | None = None
        self._thumbnail_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        app = self.app
        with Horizontal():
            with Vertical(classes="left-panel"):
                yield DataTable(id="mod-table", cursor_type="row")
                yield Label("Select a mod row for actions", id="hint-text")
                yield ThumbnailWidget(id="mod-thumbnail")
                yield ModActionPanel(id="mod-actions")
            with Vertical(classes="right-panel"):
                yield Label("Quick Actions", classes="section-header")
                yield Button("Launch Game", id="launch-btn", variant="primary")
                yield Button("Open Game Folder", id="open-folder-btn")
                yield Button("Add Mods", id="add-mod-btn")
                yield Button("Options", id="options-btn")
                yield Button("Help (F1)", id="help-btn")
                yield Button("Credits", id="credits-btn")
                yield Button("Exit", id="exit-btn", variant="error")
                yield Static("", classes="separator")
                yield StatusPanel(id="status-panel")
                yield Static("", classes="separator")
                yield KeyHints(self, id="key-hints")
        with Horizontal(id="download-bar"):
            yield ProgressBar(id="download-progress", show_eta=False, show_percentage=True)
            yield Label("", id="download-file-label")
        with Horizontal(id="bottom-status-bar"):
            yield Label("", id="bottom-progress-label")

    def on_mount(self) -> None:
        self._image_service = ThumbnailService()
        if not supports_image_protocol():
            self.notify(
                "Terminal does not support image display. Using text-based thumbnails.",
                timeout=5,
                severity="warning",
            )
        table = self.query_one("#mod-table", DataTable)
        table.columns.clear()
        table.add_column("Mod", width=None)
        table.add_column("Version", width=None)
        table.add_column("Status", width=None)
        table.add_column("Size", width=None)
        self._refresh_mods()
        self._refresh_status()
        self._poll_task = self.set_interval(2.0, self._poll_status)
        table.focus()

    def on_unmount(self) -> None:
        if self._thumbnail_task and not self._thumbnail_task.done():
            self._thumbnail_task.cancel()

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
            hint.update("Select a row for actions")
        else:
            hint.update("Press a or click Add Mods")
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
        if mods and self.selected_mod is None:
            self.selected_mod = mods[0]
        elif self.selected_mod and self.selected_mod not in mods:
            self.selected_mod = None

    def _refresh_status(self):
        app = self.app
        self.install_status = app.mod_service.get_installation_status()
        self.query_one("#status-panel", StatusPanel).refresh_status(self.install_status)

    def _poll_status(self) -> None:
        self._refresh_status()
        self._refresh_download_progress()

    def _refresh_download_progress(self):
        bar = self.query_one("#download-bar")
        pb = self.query_one("#download-progress", ProgressBar)
        fl = self.query_one("#download-file-label", Label)
        bp = self.query_one("#bottom-progress-label", Label)
        downloading_mod = None
        for mod in self.added_mods:
            if mod.downloading:
                downloading_mod = mod
                break
        if downloading_mod and downloading_mod.mod_info:
            prog = self.app.mod_service.get_download_progress(downloading_mod.mod_info.mod_name)
            bar.display = True
            if prog.total_download_size > 0:
                pb.total = prog.total_download_size
                pb.progress = prog.downloaded_size
                pct = (prog.downloaded_size / prog.total_download_size) * 100
                fl.update(prog.current_file or "")
                bp.update(f"Downloading: {downloading_mod.mod_info.mod_name} ({pct:.0f}%)")
                if prog.downloaded:
                    bar.display = False
                    fl.update("")
                    bp.update("")
            else:
                fl.update(prog.current_file or "")
                bp.update(f"Downloading: {downloading_mod.mod_info.mod_name}")
        else:
            bar.display = False
            fl.update("")
            bp.update("")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        table = self.query_one("#mod-table", DataTable)
        row_key = event.row_key
        if row_key is None:
            self.selected_mod = None
            return
        rows = table.rows
        if row_key not in rows:
            self.selected_mod = None
            return
        idx = list(rows.keys()).index(row_key)
        if idx < len(self.added_mods):
            self.selected_mod = self.added_mods[idx]

    def watch_selected_mod(self, mod: Mod | None) -> None:
        action_panel = self.query_one("#mod-actions", ModActionPanel)
        hint = self.query_one("#hint-text", Label)
        thumbnail = self.query_one("#mod-thumbnail", ThumbnailWidget)
        action_panel.show_for_mod(mod)
        if mod is not None:
            hint.display = False
            placeholder = mod.mod_info.mod_name if mod.mod_info and mod.mod_info.mod_name else "(no name)"
            thumbnail.set_image(None, placeholder=placeholder)
            thumbnail.display = True
            if self._thumbnail_task and not self._thumbnail_task.done():
                self._thumbnail_task.cancel()
            self._thumbnail_task = asyncio.ensure_future(self._load_thumbnail(mod))
        else:
            hint.display = True
            thumbnail.display = False

    async def _load_thumbnail(self, mod: Mod) -> None:
        try:
            await self.app.mod_service._ensure_mod_data(mod)
            url = mod.mod_data.ui_image_source_link if mod.mod_data else None
            name = mod.mod_info.mod_name if mod.mod_info else ""
            if not url or not name:
                return
            svc = self._image_service
            if svc is None:
                return
            cache_path = await svc.fetch_thumbnail(url, name)
            if cache_path is None:
                return
            png_data, w, h = ThumbnailService.load_and_resize(cache_path)
            thumbnail = self.query_one("#mod-thumbnail", ThumbnailWidget)
            thumbnail.set_image(png_data, w=w, h=h)
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Failed to load thumbnail")

    async def _action_wrapper(self, action_fn):
        try:
            r = action_fn()
            if asyncio.iscoroutine(r):
                await r
        except Exception as e:
            logger.exception("Action failed")
            self.notify(str(e), severity="error")
        self._refresh_mods()

    async def _do_download(self, mod: Mod):
        name = mod.mod_info.mod_name if mod.mod_info else "?"
        self.notify(f"Downloading {name}...", timeout=2)
        try:
            await self.app.mod_service.download_mod(name)
            self.notify(f"{name} downloaded", severity="information")
        except Exception as e:
            logger.exception("Download failed")
            self.notify(f"Download failed: {e}", severity="error")
        self._refresh_mods()

    async def _do_install(self, mod: Mod):
        name = mod.mod_info.mod_name if mod.mod_info else "?"
        opts = self.app.options_service.get_options()
        try:
            await self.app.mod_service.ensure_gentool_installed(opts.install_method)
            replaced = self.app.mod_service.install_mod(name, opts.install_method)
            if replaced:
                self.notify(f"Replaced {replaced} with {name}", severity="information")
            else:
                self.notify(f"{name} installed", severity="information")
        except Exception as e:
            logger.exception("Install failed")
            self.notify(f"Install failed: {e}", severity="error")
        self._refresh_mods()

    def _do_uninstall(self, mod: Mod):
        name = mod.mod_info.mod_name if mod.mod_info else "?"
        try:
            self.app.mod_service.uninstall_mod(name)
            self.notify(f"{name} uninstalled", severity="information")
        except Exception as e:
            logger.exception("Uninstall failed")
            self.notify(f"Uninstall failed: {e}", severity="error")
        self._refresh_mods()

    def _do_delete(self, mod: Mod):
        name = mod.mod_info.mod_name if mod.mod_info else "?"
        try:
            self.app.mod_service.delete_mod(name)
            self.notify(f"{name} files deleted", severity="information")
        except Exception as e:
            logger.exception("Delete failed")
            self.notify(f"Delete failed: {e}", severity="error")
        self._refresh_mods()

    def _do_remove(self, mod: Mod):
        name = mod.mod_info.mod_name if mod.mod_info else "?"
        try:
            self.app.mod_service.remove_mod_from_list(name)
            self.notify(f"{name} removed", severity="information")
        except Exception as e:
            logger.exception("Remove failed")
            self.notify(f"Remove failed: {e}", severity="error")
        self._refresh_mods()

    def action_show_help(self) -> None:
        from genlauncher_tui.screens.help_screen import HelpScreen
        self.app.push_screen(HelpScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch-btn":
            import webbrowser
            webbrowser.open("steam://rungameid/2732960")
        elif event.button.id == "open-folder-btn":
            try:
                path = SteamService.get_game_install_dir()
                if sys.platform == "win32":
                    subprocess.run(["explorer", path])
                elif sys.platform == "darwin":
                    subprocess.run(["open", path])
                else:
                    subprocess.run(["xdg-open", path])
            except Exception as e:
                self.notify(f"Failed to open folder: {e}", severity="error")
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
        elif event.button.id == "act-download":
            if self.selected_mod:
                asyncio.ensure_future(self._do_download(self.selected_mod))
        elif event.button.id == "act-install":
            if self.selected_mod:
                asyncio.ensure_future(self._action_wrapper(lambda m=self.selected_mod: self._do_install(m)))
        elif event.button.id == "act-uninstall":
            if self.selected_mod:
                asyncio.ensure_future(self._action_wrapper(lambda m=self.selected_mod: self._do_uninstall(m)))
        elif event.button.id == "act-delete":
            if self.selected_mod:
                asyncio.ensure_future(self._action_wrapper(lambda m=self.selected_mod: self._do_delete(m)))
        elif event.button.id == "act-remove":
            if self.selected_mod:
                asyncio.ensure_future(self._action_wrapper(lambda m=self.selected_mod: self._do_remove(m)))


def _format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "-"
    mb = size_bytes / (1024 * 1024)
    if mb < 1024:
        return f"{mb:.0f} MB"
    gb = mb / 1024
    return f"{gb:.1f} GB"
