from __future__ import annotations

import asyncio
import logging
from typing import Any
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import DataTable, Button, Label, LoadingIndicator, Header, Footer

from genlauncher_tui.models.repo import ModAddonsAndPatches, ReposModsData


logger = logging.getLogger(__name__)


class AddModScreen(Screen):
    @property
    def app(self) -> Any:
        return super().app

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    highlighted_mod: reactive[ModAddonsAndPatches | None] = reactive(None)

    def __init__(self):
        super().__init__()
        self._repo_data: ReposModsData | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Label("Available Mods", id="add-mod-title")
            yield LoadingIndicator(id="loading")
            yield DataTable(id="avail-mod-table", cursor_type="row")
            yield Label("", id="help-text")
            yield Label("", id="error-text")
            with Horizontal():
                yield Button("Add Selected Mod", id="add-mod-btn", variant="primary")
                yield Button("Retry", id="retry-btn", variant="default")
                yield Button("Back", id="back-btn", variant="default")

    async def on_mount(self) -> None:
        self.query_one("#avail-mod-table", DataTable).display = False
        self.query_one("#loading", LoadingIndicator).display = True
        self.query_one("#retry-btn", Button).display = False
        self.query_one("#error-text", Label).display = False
        self.query_one("#help-text", Label).update("Click a mod, then press Enter or click Add Selected Mod")
        await self._fetch_mods()

    def watch_highlighted_mod(self, mod: ModAddonsAndPatches | None) -> None:
        btn = self.query_one("#add-mod-btn", Button)
        btn.disabled = mod is None

    async def _fetch_mods(self):
        table = self.query_one("#avail-mod-table", DataTable)
        table.columns.clear()
        table.add_column("Mod", width=35)
        table.add_column("Patches", width=20)
        table.add_column("Addons", width=20)

        repo = self.app.repo_service
        try:
            data = await repo.fetch_repo_data()
            self.app.mod_service.set_repo_data(data)
            unadded = self.app.mod_service.get_unadded_mods()
            self._repo_data = unadded
            self.query_one("#loading", LoadingIndicator).display = False
            self.query_one("#retry-btn", Button).display = False
            self.query_one("#error-text", Label).display = False
            table.display = True
            table.clear()
            for entry in unadded.mod_datas:
                patches = ", ".join(entry.mod_patches) if entry.mod_patches else ""
                addons = ", ".join(entry.mod_addons) if entry.mod_addons else ""
                table.add_row(entry.mod_name, patches, addons)
            count = len(unadded.mod_datas)
            self.query_one("#add-mod-title", Label).update(f"Available Mods ({count})")
            if unadded.mod_datas:
                table.move_cursor(row=0)
            else:
                self.query_one("#help-text", Label).update("All mods have been added!")
        except Exception as e:
            logger.exception("Failed to fetch mods")
            self.query_one("#loading", LoadingIndicator).display = False
            self.query_one("#retry-btn", Button).display = True
            self.query_one("#error-text", Label).update(f"[red]Failed to fetch mods: {e}[/]")
            self.query_one("#error-text", Label).display = True
            self.query_one("#add-mod-title", Label).update("Available Mods")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-mod-btn":
            self._add_current_mod()
        elif event.button.id == "retry-btn":
            asyncio.ensure_future(self._retry_fetch())
        elif event.button.id == "back-btn":
            self.action_back()

    async def _retry_fetch(self) -> None:
        self.query_one("#retry-btn", Button).display = False
        self.query_one("#error-text", Label).display = False
        self.query_one("#loading", LoadingIndicator).display = True
        await self._fetch_mods()

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._add_current_mod()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if self._repo_data is None:
            return
        table = self.query_one("#avail-mod-table", DataTable)
        row_key = event.row_key
        if row_key is None:
            self.highlighted_mod = None
            return
        rows = table.rows
        if row_key not in rows:
            self.highlighted_mod = None
            return
        idx = list(rows.keys()).index(row_key)
        mod_datas = self._repo_data.mod_datas or []
        if idx < len(mod_datas):
            self.highlighted_mod = mod_datas[idx]
        else:
            self.highlighted_mod = None

    def _add_current_mod(self) -> None:
        if self.highlighted_mod is None:
            self.notify("No mod selected", severity="warning")
            return
        entry = self.highlighted_mod
        success = self.app.mod_service.add_mod_to_list(entry.mod_name)
        if success:
            self.notify(f"Added {entry.mod_name}", severity="information")
        else:
            self.notify(f"Could not add {entry.mod_name}", severity="warning")
        self._refresh_list()

    def _refresh_list(self) -> None:
        unadded = self.app.mod_service.get_unadded_mods()
        self._repo_data = unadded
        table = self.query_one("#avail-mod-table", DataTable)
        table.clear()
        for e in unadded.mod_datas:
            patches = ", ".join(e.mod_patches) if e.mod_patches else ""
            addons = ", ".join(e.mod_addons) if e.mod_addons else ""
            table.add_row(e.mod_name, patches, addons)
        count = len(unadded.mod_datas)
        self.query_one("#add-mod-title", Label).update(f"Available Mods ({count})")
        if unadded.mod_datas:
            table.move_cursor(row=0)
        else:
            self.highlighted_mod = None
            self.query_one("#help-text", Label).update("All mods have been added!")
