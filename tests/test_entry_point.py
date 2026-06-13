from unittest.mock import patch

from genlauncher_tui.__main__ import main
from genlauncher_tui.app import GenLauncherApp


def test_main_creates_app():
    with patch.object(GenLauncherApp, "run") as mock_run:
        main()
        mock_run.assert_called_once()
