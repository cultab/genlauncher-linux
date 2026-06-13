import os
import tempfile

import pytest

from genlauncher_tui.app import GenLauncherApp
from genlauncher_tui.services.mod_service import MODLIST_FILE
from genlauncher_tui.services.steam_service import SteamService


def _mod_list_path() -> str:
    try:
        return os.path.join(SteamService.get_mod_dir(), MODLIST_FILE)
    except Exception:
        return os.path.join(tempfile.gettempdir(), ".genlauncher_test_modlist.json")


@pytest.fixture(autouse=True)
def clean_state():
    path = _mod_list_path()
    if os.path.isfile(path):
        os.unlink(path)
    yield
    if os.path.isfile(path):
        os.unlink(path)


@pytest.mark.asyncio
async def test_app_starts_on_home_screen():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert "Home" in type(app.screen).__name__, f"Expected HomeScreen, got {type(app.screen).__name__}"


@pytest.mark.asyncio
async def test_home_screen_has_mod_table():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        table = app.screen.query_one("#mod-table")
        assert table is not None
        assert len(table.rows) == 0, "Home table should be empty with no mods added"


@pytest.mark.asyncio
async def test_home_screen_has_action_buttons():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        for btn_id in ("launch-btn", "add-mod-btn", "options-btn", "credits-btn", "help-btn", "exit-btn"):
            btn = app.screen.query_one(f"#{btn_id}")
            assert btn is not None, f"Missing button: {btn_id}"


@pytest.mark.asyncio
async def test_navigate_to_add_mod_screen():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        assert "AddMod" in type(app.screen).__name__, f"Expected AddModScreen, got {type(app.screen).__name__}"


@pytest.mark.asyncio
async def test_navigate_to_options_screen():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        assert "Options" in type(app.screen).__name__, f"Expected OptionsScreen, got {type(app.screen).__name__}"


@pytest.mark.asyncio
async def test_navigate_to_credits_screen():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("c")
        await pilot.pause()
        assert "Credits" in type(app.screen).__name__, f"Expected CreditsScreen, got {type(app.screen).__name__}"


@pytest.mark.asyncio
async def test_escape_returns_from_sub_screens():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        for key in ("a", "o", "c"):
            await pilot.press(key)
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
        assert "Home" in type(app.screen).__name__, f"Expected HomeScreen, got {type(app.screen).__name__}"


@pytest.mark.asyncio
async def test_add_mod_flow_keyboard():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Go to Add Mod screen
        await pilot.press("a")
        await pilot.pause(2)

        # Should show mods
        unadded = app.mod_service.get_unadded_mods()
        assert len(unadded.mod_datas) > 0, "Expected mods to be fetched"
        initial_count = len(unadded.mod_datas)

        # Press Enter to add the first highlighted mod
        await pilot.press("enter")
        await pilot.pause()

        remaining = len(app.mod_service.get_unadded_mods().mod_datas)
        assert remaining == initial_count - 1, f"Expected {initial_count - 1} remaining, got {remaining}"


@pytest.mark.asyncio
async def test_add_mod_flow_button():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause(2)

        initial_count = len(app.mod_service.get_unadded_mods().mod_datas)

        # Click the Add Selected Mod button
        await pilot.click("#add-mod-btn")
        await pilot.pause()

        remaining = len(app.mod_service.get_unadded_mods().mod_datas)
        assert remaining == initial_count - 1, f"Expected {initial_count - 1} remaining, got {remaining}"


@pytest.mark.asyncio
async def test_added_mod_shows_on_home_screen():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Add one mod
        await pilot.press("a")
        await pilot.pause(2)
        await pilot.click("#add-mod-btn")
        await pilot.pause()

        # Go home
        await pilot.press("escape")
        await pilot.pause()

        # The home screen table should now have 1 row
        table = app.screen.query_one("#mod-table")
        assert len(table.rows) == 1, f"Expected 1 row, got {len(table.rows)}"


@pytest.mark.asyncio
async def test_multiple_adds_reflect_on_home():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause(2)

        # Add first mod
        await pilot.click("#add-mod-btn")
        await pilot.pause(0.5)

        added = app.mod_service.get_added_mods()
        assert len(added) == 1, f"Expected 1 after first add, got {len(added)}"

        # Add second mod
        await pilot.click("#add-mod-btn")
        await pilot.pause(0.5)

        added = app.mod_service.get_added_mods()
        assert len(added) == 2, f"Expected 2 after second add, got {len(added)}"

        # Go home
        await pilot.press("escape")
        await pilot.pause()

        table = app.screen.query_one("#mod-table")
        assert len(table.rows) == 2, f"Expected 2 rows, got {len(table.rows)}"


@pytest.mark.asyncio
async def test_home_persists_across_screen_navigation():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause(2)

        # Add 2 mods, checking service state each time
        await pilot.click("#add-mod-btn")
        await pilot.pause(0.5)
        assert len(app.mod_service.get_added_mods()) == 1

        await pilot.click("#add-mod-btn")
        await pilot.pause(0.5)
        assert len(app.mod_service.get_added_mods()) == 2

        await pilot.press("escape")
        await pilot.pause()

        table = app.screen.query_one("#mod-table")
        assert len(table.rows) == 2

        # Go to options and back
        await pilot.press("o")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        # Go to credits and back
        await pilot.press("c")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        # Home should still show 2 mods
        table = app.screen.query_one("#mod-table")
        assert len(table.rows) == 2, f"Expected 2 rows after navigation, got {len(table.rows)}"


@pytest.mark.asyncio
async def test_help_screen_f1():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("f1")
        await pilot.pause()
        assert "Help" in type(app.screen).__name__, f"Expected HelpScreen, got {type(app.screen).__name__}"
        dialog = app.screen.query_one("#help-dialog")
        assert dialog is not None


@pytest.mark.asyncio
async def test_help_screen_question_mark():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("?")
        await pilot.pause()
        assert "Help" in type(app.screen).__name__


@pytest.mark.asyncio
async def test_help_screen_help_button():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.click("#help-btn")
        await pilot.pause()
        assert "Help" in type(app.screen).__name__


@pytest.mark.asyncio
async def test_help_screen_dismisses_with_escape():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("f1")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert "Home" in type(app.screen).__name__, "Escape should return to HomeScreen from Help"


@pytest.mark.asyncio
async def test_help_screen_dismisses_with_close_button():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.click("#help-btn")
        await pilot.pause()
        await pilot.click("#close-help-btn")
        await pilot.pause()
        assert "Home" in type(app.screen).__name__


@pytest.mark.asyncio
async def test_help_screen_shows_keybindings():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("f1")
        await pilot.pause()
        dialog = app.screen.query_one("#help-dialog")
        # Dialog exists
        assert dialog is not None
        # Close button exists
        assert dialog.query_one("#close-help-btn") is not None
        # Multiple key-row sections (one per keybinding)
        key_rows = dialog.query(".key-row")
        assert len(key_rows) >= 6, f"Expected at least 6 keybindings listed, got {len(key_rows)}"
        await pilot.press("escape")


@pytest.mark.asyncio
async def test_quit_works():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()
        assert app._running is False


@pytest.mark.asyncio
async def test_options_screen_saves_install_method():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        assert "Options" in type(app.screen).__name__

        # Set the radio to Copy via widget API, then click Save
        radio_set = app.screen.query_one("#install-method-set")
        radio_set.index = 1
        await pilot.pause()

        await pilot.click("#save-btn")
        await pilot.pause()

        opts = app.options_service.get_options()
        assert opts.install_method.value == "CopyFiles"


@pytest.mark.asyncio
async def test_options_screen_resets_to_defaults():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()

        # Change to Copy via widget API, then Save
        radio_set = app.screen.query_one("#install-method-set")
        radio_set.index = 1
        await pilot.pause()

        await pilot.click("#save-btn")
        await pilot.pause()
        assert app.options_service.get_options().install_method.value == "CopyFiles"

        # Reset
        await pilot.click("#reset-btn")
        await pilot.pause()

        # Should revert to default (SymLink on Linux)
        opts = app.options_service.get_options()
        assert opts.install_method.value == "SymLink"


@pytest.mark.asyncio
async def test_options_screen_back_button():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        await pilot.click("#back-btn")
        await pilot.pause()
        assert "Home" in type(app.screen).__name__


@pytest.mark.asyncio
async def test_credits_screen_back_button():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("c")
        await pilot.pause()
        assert "Credits" in type(app.screen).__name__
        await pilot.click("#back-btn")
        await pilot.pause()
        assert "Home" in type(app.screen).__name__


@pytest.mark.asyncio
async def test_launch_button_exists():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        btn = app.screen.query_one("#launch-btn")
        assert btn is not None
        assert btn.label == "Launch Game"


@pytest.mark.asyncio
async def test_mod_actions_appear_on_row_select():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause(2)
        await pilot.click("#add-mod-btn")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        table = app.screen.query_one("#mod-table")
        assert len(table.rows) == 1

        # Select the row — action buttons should appear
        await pilot.press("enter")
        await pilot.pause()

        actions_container = app.screen.query_one("#mod-actions")
        assert actions_container.display is True


@pytest.mark.asyncio
async def test_mod_actions_show_correct_buttons():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause(2)
        await pilot.click("#add-mod-btn")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        # Select the row
        await pilot.press("enter")
        await pilot.pause()

        # For an un-downloaded, un-installed mod: Download + Remove visible
        download_btn = app.screen.query_one("#act-download")
        remove_btn = app.screen.query_one("#act-remove")
        install_btn = app.screen.query_one("#act-install")
        assert download_btn.display is True
        assert remove_btn.display is True
        assert install_btn.display is False


@pytest.mark.asyncio
async def test_remove_mod_from_list_via_action_button():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause(2)
        await pilot.click("#add-mod-btn")
        await pilot.pause()

        added = app.mod_service.get_added_mods()
        assert len(added) == 1

        await pilot.press("escape")
        await pilot.pause()

        # Select the row
        await pilot.press("enter")
        await pilot.pause()

        # Click Remove
        await pilot.click("#act-remove")
        await pilot.pause()

        remaining = app.mod_service.get_added_mods()
        assert len(remaining) == 0
        table = app.screen.query_one("#mod-table")
        assert len(table.rows) == 0


@pytest.mark.asyncio
async def test_mod_action_keeps_home_screen():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause(2)
        await pilot.click("#add-mod-btn")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        await pilot.click("#act-remove")
        await pilot.pause()

        # Should still be on HomeScreen (no modal)
        assert "Home" in type(app.screen).__name__
