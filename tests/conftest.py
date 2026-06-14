import asyncio
import json
import os
import tempfile
from unittest.mock import patch

import pytest

from genlauncher_tui.app import GenLauncherApp
from genlauncher_tui.services.steam_service import SteamService


@pytest.fixture(autouse=True)
def _tmp_mod_dir():
    """Patch SteamService.get_mod_dir to a temp dir so tests never touch real mod data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.object(SteamService, "get_mod_dir", return_value=tmpdir):
            yield


@pytest.fixture
def clean_state():
    yield


@pytest.fixture
async def app():
    a = GenLauncherApp()
    async with a.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        yield pilot, a
