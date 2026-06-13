import asyncio
import json
import os
import shutil

import pytest

from genlauncher_tui.app import GenLauncherApp
from genlauncher_tui.services.steam_service import SteamService


def _clean_mod_list():
    try:
        mod_dir = SteamService.get_mod_dir()
        json_path = os.path.join(mod_dir, "genlauncher_modlist.json")
        if os.path.isfile(json_path):
            os.unlink(json_path)
    except Exception:
        pass


def _backup_mod_list() -> tuple[str | None, str | None]:
    try:
        mod_dir = SteamService.get_mod_dir()
        json_path = os.path.join(mod_dir, "genlauncher_modlist.json")
        if os.path.isfile(json_path):
            backup_path = json_path + ".bak"
            shutil.copy2(json_path, backup_path)
            os.unlink(json_path)
            return json_path, backup_path
    except Exception:
        pass
    return None, None


def _restore_mod_list(orig_path: str | None, backup_path: str | None):
    if orig_path and backup_path and os.path.isfile(backup_path):
        try:
            os.makedirs(os.path.dirname(orig_path), exist_ok=True)
            shutil.move(backup_path, orig_path)
        except Exception:
            pass


@pytest.fixture
def clean_state():
    orig, backup = _backup_mod_list()
    yield
    _restore_mod_list(orig, backup)


@pytest.fixture
async def app():
    orig, backup = _backup_mod_list()
    a = GenLauncherApp()
    async with a.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        yield pilot, a
    _restore_mod_list(orig, backup)
