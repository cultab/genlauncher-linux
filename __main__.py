from genlauncher_tui.app import GenLauncherApp
from genlauncher_tui.logging_setup import setup_logging


def main():
    setup_logging()
    app = GenLauncherApp()
    app.run()


if __name__ == "__main__":
    main()
