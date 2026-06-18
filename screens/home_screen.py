from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Button, Header, Label, ListItem, ListView, ProgressBar

from genlauncher_tui.models.mod import Mod, standard_mod_name
from genlauncher_tui.models.options import InstallationStatus
from genlauncher_tui.services.image_service import ThumbnailService
from genlauncher_tui.services.steam_service import SteamService
from genlauncher_tui.widgets.key_hints import KeyHints
from genlauncher_tui.widgets.mod_row import ModRow
from genlauncher_tui.widgets.status_panel import StatusPanel
from genlauncher_tui.widgets.thumbnail import ThumbnailWidget

if TYPE_CHECKING:
    from genlauncher_tui.app import GenLauncherApp

logger = logging.getLogger(__name__)


class HomeScreen(Screen):
    @property
    def app(self) -> GenLauncherApp:
        return super().app  # type: ignore[return-value]

    BINDINGS = [
        Binding("f1", "show_help", "Help"),
        Binding("?", "show_help", "Help"),
    ]

    added_mods: reactive[list[Mod]] = reactive([])
    install_status: reactive[InstallationStatus] = reactive(InstallationStatus())

    def __init__(self):
        super().__init__()
        self._poll_task: Timer | None = None
        self._image_service: ThumbnailService | None = None
        self._thumbnail_task: asyncio.Task | None = None
        self._thumbnail_cache: dict[str, tuple[bytes, int, int]] = {}
        self._thumb_refs: dict[str, ThumbnailWidget] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="toolbar"):
            yield Button("Launch Game", id="launch-btn", variant="primary")
            yield Button("Open Folder", id="open-folder-btn")
            yield Button("Add Mods", id="add-mod-btn")
            yield Button("Options", id="options-btn")
            yield Button("Help (F1)", id="help-btn")
            yield Button("Credits", id="credits-btn")
            yield Button("Exit", id="exit-btn", variant="error")
        with Horizontal():
            with Vertical(classes="mod-list-panel"):
                yield Label("No mods added — press a to add mods", id="empty-list-label")
                yield ListView(id="mod-list")
            with Vertical(classes="right-panel"):
                yield StatusPanel(id="status-panel")
                yield KeyHints(self, id="key-hints")
        with Horizontal(id="download-bar"):
            yield ProgressBar(id="download-progress", show_eta=False, show_percentage=True)
            yield Label("", id="download-file-label")
        with Horizontal(id="bottom-status-bar"):
            yield Label("", id="bottom-progress-label")

    def on_mount(self) -> None:
        self._image_service = ThumbnailService()
        self._refresh_mods()
        self._refresh_status()
        self._poll_task = self.set_interval(2.0, self._poll_status)
        list_view = self.query_one("#mod-list", ListView)
        list_view.focus()

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
        list_view = self.query_one("#mod-list", ListView)
        empty_label = self.query_one("#empty-list-label", Label)
        list_view.clear()
        self._thumb_refs.clear()
        empty = not bool(mods)
        empty_label.display = empty
        list_view.display = not empty
        for i, mod in enumerate(mods):
            row = ModRow(mod, i)
            list_view.append(ListItem(row))
            if mod.mod_info:
                cell = row.thumbnail_cell
                if cell is not None:
                    self._thumb_refs[mod.mod_info.mod_name] = cell
        if self._thumbnail_task and not self._thumbnail_task.done():
            self._thumbnail_task.cancel()
        self._thumbnail_task = asyncio.create_task(self._load_all_thumbnails(mods))

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

    async def _load_all_thumbnails(self, mods: list[Mod]) -> None:
        for mod in mods:
            try:
                if not mod.mod_info:
                    continue
                name = mod.mod_info.mod_name
                key = standard_mod_name(name)
                if key in self._thumbnail_cache:
                    png_data, w, h = self._thumbnail_cache[key]
                    self._update_row_thumbnail(name, png_data, w, h)
                    continue
                try:
                    await self.app.mod_service._ensure_mod_data(mod)
                except Exception:
                    continue
                url = mod.mod_data.ui_image_source_link if mod.mod_data else None
                if not url:
                    continue
                svc = self._image_service
                if svc is None:
                    continue
                try:
                    cache_path = await svc.fetch_thumbnail(url, name)
                except Exception:
                    continue
                if cache_path is None:
                    continue
                png_data, w, h = ThumbnailService.load_and_resize(cache_path)
                self._thumbnail_cache[key] = (png_data, w, h)
                self._update_row_thumbnail(name, png_data, w, h)
            except Exception:
                pass

    def _update_row_thumbnail(self, mod_name: str, png_data: bytes, w: int, h: int) -> None:
        thumb = self._thumb_refs.get(mod_name)
        if thumb is not None:
            thumb.set_image(png_data, w=w, h=h)

    # --- Action methods ---

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

    async def _do_install_gentool(self):
        opts = self.app.options_service.get_options()
        try:
            await self.app.mod_service.ensure_gentool_installed(opts.install_method)
            self.notify("GenTool installed", severity="information")
        except Exception as e:
            logger.exception("GenTool install failed")
            self.notify(f"GenTool install failed: {e}", severity="error")
        self._refresh_status()

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
        btn_id = event.button.id
        if not btn_id:
            return

        if btn_id == "launch-btn":
            import webbrowser
            webbrowser.open("steam://rungameid/2732960")
        elif btn_id == "open-folder-btn":
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
        elif btn_id == "add-mod-btn":
            self.app.action_go_add_mod()
        elif btn_id == "options-btn":
            self.app.action_go_options()
        elif btn_id == "help-btn":
            self.action_show_help()
        elif btn_id == "credits-btn":
            self.app.action_go_credits()
        elif btn_id == "exit-btn":
            self.app.exit()
        elif btn_id == "install-gentool-btn":
            asyncio.create_task(self._do_install_gentool())
        else:
            self._handle_mod_action(btn_id)

    def _find_mod_for_action(self, btn_id: str) -> Mod | None:
        parts = btn_id.split("-", 1)
        if len(parts) != 2:
            return None
        try:
            idx = int(parts[1])
        except ValueError:
            return None
        if 0 <= idx < len(self.added_mods):
            return self.added_mods[idx]
        return None

    def _handle_mod_action(self, btn_id: str) -> None:
        mod = self._find_mod_for_action(btn_id)
        if mod is None:
            return
        if btn_id.startswith("dl-"):
            asyncio.create_task(self._do_download(mod))
        elif btn_id.startswith("inst-"):
            asyncio.create_task(self._do_install(mod))
        elif btn_id.startswith("uninst-"):
            self._do_uninstall(mod)
        elif btn_id.startswith("del-"):
            self._do_delete(mod)
        elif btn_id.startswith("rem-"):
            self._do_remove(mod)
