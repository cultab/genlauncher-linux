# genlauncher-linux

**This project is vibecoded.** The entirety of this codebase was generated through AI assistance (opencode's free models, but they ran out so we're on a local 50k context gemma4 from ollama) on a weekend. Commits have NOT been thoroughly reviewed by a human; use at your own risk.

The human involvement was limited to:

* "hey this is broken fix it"
* "add this feature"
* and lastly "this looks like crap, do it better"
* also writing parts of `README.md` and `AGENTS.md` I guess

Terminal UI mod manager for Command & Conquer: Generals - Zero Hour (Steam version). Code ported to python + the textual library from [GenLauncherWeb](https://github.com/Tricky12321/GenLauncherWeb).

## Install

From source:

```bash
git clone https://github.com/cultab/genlauncher-linux
cd genlauncher-linux
# recommended:
pipx install .
# or if you don't have pipx
pip install .
```

## Usage

Run `genlauncher` from your terminal.
You can also run genlauncher-web to open the same ui in a browser.

## Requirements

- Python 3.10+
- Steam with Command & Conquer: Generals - Zero Hour installed

## Test

Tests were the main way of getting this to actually work, because the agents broke things with every change.

```bash
python -m pytest tests/ -v
```

## License

CC0 1.0 Universal (Creative Commons Zero) — see `LICENSE`.

Basically public domain, because it's vibecoded.

## Thanks

* The linux compatible: [GenLauncherWeb](https://github.com/Tricky12321/GenLauncherWeb)
* The original: [GenLauncher](https://www.moddb.com/mods/genlauncher)
