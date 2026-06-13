import asyncio
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


@pytest.fixture
def clean_state():
    _clean_mod_list()
    yield
    _clean_mod_list()


@pytest.fixture
async def app():
    _clean_mod_list()
    a = GenLauncherApp()
    async with a.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        yield pilot, a
