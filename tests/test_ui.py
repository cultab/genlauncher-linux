import os
import tempfile

import pytest
from textual.widgets import Button

from genlauncher_tui.app import GenLauncherApp
from genlauncher_tui.services.mod_utils import MODLIST_FILE
from genlauncher_tui.services.steam_service import SteamService


def _mod_list_path() -> str:
    try:
        return os.path.join(SteamService.get_mod_dir(), MODLIST_FILE)
    except Exception:
        return os.path.join(tempfile.gettempdir(), ".genlauncher_test_modlist.json")


@pytest.mark.asyncio
async def test_app_starts_on_home_screen():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert "Home" in type(app.screen).__name__, f"Expected HomeScreen, got {type(app.screen).__name__}"


@pytest.mark.asyncio
async def test_home_screen_has_mod_list():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        list_view = app.screen.query_one("#mod-list")
        assert list_view is not None
        assert len(list_view.children) == 0, "Mod list should be empty with no mods added"


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
        datas = unadded.mod_datas or []
        assert len(datas) > 0, "Expected mods to be fetched"
        initial_count = len(datas)

        # Press Enter to add the first highlighted mod
        await pilot.press("enter")
        await pilot.pause()

        remaining = len(app.mod_service.get_unadded_mods().mod_datas or [])
        assert remaining == initial_count - 1, f"Expected {initial_count - 1} remaining, got {remaining}"


@pytest.mark.asyncio
async def test_add_mod_flow_button():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause(2)

        datas = app.mod_service.get_unadded_mods().mod_datas or []
        initial_count = len(datas)

        # Click the Add Selected Mod button
        await pilot.click("#add-mod-btn")
        await pilot.pause()

        remaining = len(app.mod_service.get_unadded_mods().mod_datas or [])
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

        # The home screen list should now have 1 item
        list_view = app.screen.query_one("#mod-list")
        assert len(list_view.children) == 1, f"Expected 1 item, got {len(list_view.children)}"


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

        list_view = app.screen.query_one("#mod-list")
        assert len(list_view.children) == 2, f"Expected 2 items, got {len(list_view.children)}"


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

        list_view = app.screen.query_one("#mod-list")
        assert len(list_view.children) == 2

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
        list_view = app.screen.query_one("#mod-list")
        assert len(list_view.children) == 2, f"Expected 2 items after navigation, got {len(list_view.children)}"


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
async def test_mod_buttons_show_correct_states():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause(2)
        await pilot.click("#add-mod-btn")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        # For an un-downloaded, un-installed mod at index 0:
        # Download (dl-0) visible, Remove (rem-0) visible, Install (inst-0) hidden
        download_btn = app.screen.query_one("#dl-0")
        remove_btn = app.screen.query_one("#rem-0")
        install_btn = app.screen.query_one("#inst-0")
        assert download_btn is not None
        assert remove_btn is not None
        assert install_btn is not None
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
        await pilot.pause()

        # Use press() instead of pilot.click because Textual's ListView
        # intercepts mouse clicks on child buttons, preventing Button.Pressed from firing.
        app.screen.query_one("#rem-0", Button).press()
        await pilot.pause()

        remaining = app.mod_service.get_added_mods()
        assert len(remaining) == 0
        list_view = app.screen.query_one("#mod-list")
        assert len(list_view.children) == 0


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

        app.screen.query_one("#rem-0", Button).press()
        await pilot.pause()

        # Should still be on HomeScreen (no modal)
        assert "Home" in type(app.screen).__name__


@pytest.mark.asyncio
async def test_home_screen_bottom_status_bar():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        bar = app.screen.query_one("#bottom-status-bar")
        assert bar is not None


@pytest.mark.asyncio
async def test_home_screen_right_panel_section_headers():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        status_panel = app.screen.query_one("#status-panel")
        assert status_panel is not None
        assert status_panel.display is True


@pytest.mark.asyncio
async def test_home_screen_has_key_hints():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        key_hints = app.screen.query_one("#key-hints")
        assert key_hints is not None
        key_rows = key_hints.query(".key-row")
        assert len(key_rows) >= 6, f"Expected at least 6 key hints, got {len(key_rows)}"


@pytest.mark.asyncio
async def test_empty_label_hides_when_mods_present():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Initially empty, label should be visible
        empty_label = app.screen.query_one("#empty-list-label")
        assert empty_label.display is True

        await pilot.press("a")
        await pilot.pause(2)
        await pilot.click("#add-mod-btn")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        # After adding a mod, empty label should be hidden
        empty_label = app.screen.query_one("#empty-list-label")
        assert empty_label.display is False


@pytest.mark.asyncio
async def test_add_mod_screen_has_retry_button():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause(2)
        retry_btn = app.screen.query_one("#retry-btn")
        assert retry_btn is not None
        assert retry_btn.label == "Retry"


@pytest.mark.asyncio
async def test_add_mod_screen_has_error_text():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause(2)
        error_text = app.screen.query_one("#error-text")
        assert error_text is not None


@pytest.mark.asyncio
async def test_add_mod_screen_shows_mod_count():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause(2)
        title = app.screen.query_one("#add-mod-title")
        title_text = str(title.render())
        assert "(" in title_text, f"Expected mod count in title, got '{title_text}'"
        assert ")" in title_text


@pytest.mark.asyncio
async def test_add_mod_button_labels_clean():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause(2)
        add_btn = app.screen.query_one("#add-mod-btn")
        assert add_btn.label == "Add Selected Mod", f"Expected 'Add Selected Mod', got '{add_btn.label}'"
        back_btn = app.screen.query_one("#back-btn")
        assert back_btn.label == "Back", f"Expected 'Back', got '{back_btn.label}'"


@pytest.mark.asyncio
async def test_options_screen_has_footer():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        footer = app.screen.query_one("Footer")
        assert footer is not None


@pytest.mark.asyncio
async def test_credits_screen_has_footer():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.press("c")
        await pilot.pause()
        footer = app.screen.query_one("Footer")
        assert footer is not None


@pytest.mark.asyncio
async def test_inline_mod_buttons_exist():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        await pilot.press("a")
        await pilot.pause(2)
        await pilot.click("#add-mod-btn")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        # Verify all inline buttons exist for row 0
        assert app.screen.query_one("#dl-0") is not None
        assert app.screen.query_one("#inst-0") is not None
        assert app.screen.query_one("#uninst-0") is not None
        assert app.screen.query_one("#del-0") is not None
        assert app.screen.query_one("#rem-0") is not None


@pytest.mark.asyncio
async def test_status_panel_widget():
    app = GenLauncherApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        from genlauncher_tui.widgets.status_panel import StatusPanel
        sp = app.screen.query_one("#status-panel", StatusPanel)
        assert sp is not None
        assert sp.query_one("#gen-tool-status") is not None
        assert sp.query_one("#modded-launcher-status") is not None
        assert sp.query_one("#steam-path-label") is not None
