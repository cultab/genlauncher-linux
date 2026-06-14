"""Script to serve GenLauncher TUI over the web via textual serve."""
from __future__ import annotations

import sys
import webbrowser

HOST = "localhost"
PORT = 8000


def main():
    from textual_serve.server import Server

    webbrowser.open(f"http://{HOST}:{PORT}")
    server = Server(
        f"{sys.executable} -m genlauncher_tui",
        host=HOST,
        port=PORT,
    )
    server.serve()


if __name__ == "__main__":
    main()
