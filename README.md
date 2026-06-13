# GenLauncher TUI

**This project is VIBE-coded.** The majority of this codebase was generated through AI assistance (opencode's free models, but they ran out so we're on a local 50k context gemma4 from ollama) on weekends. Commits have NOT been thoroughly reviewed by a human — use at your own risk.

Terminal UI mod manager for Command & Conquer: Generals - Zero Hour (Steam version).

## Install

From source:

```bash
pip install .
```

Or isolated with pipx:

```bash
pipx install .
```

## Usage

Run `genlauncher` from your terminal.

| Key | Action |
|---|---|
| `a` | Browse available mods |
| `o` | Open options |
| `c` | View credits |
| `l` | Launch Zero Hour via Steam |
| `F1` / `?` | Show help |
| `q` | Quit |
| `Esc` | Go back |

## Requirements

- Python 3.10+
- Steam with Command & Conquer: Generals - Zero Hour installed
- Optional: `pip install .[archive]` for 7z/RAR archive support (py7zr, rarfile)

## Test

```bash
python -m pytest tests/ -v
```

## License

CC0 1.0 Universal (Creative Commons Zero) — see `LICENSE`.


