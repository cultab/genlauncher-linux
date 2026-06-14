# GenLauncher TUI — Agent Instructions

Terminal UI mod manager for Command & Conquer: Generals - Zero Hour.
Built with [Textual](https://textual.textualize.io/) v1+, Python 3.10+.

## Commands

```bash
pip install -e ".[archive]"        # editable install with archive support
genlauncher                        # launch the TUI (also: python -m genlauncher_tui)
python -m pytest tests/ -v         # run full suite before commits
python -m pytest tests/test_ui.py -v -k "test_name"  # single UI test
```

## Architecture (non-obvious from filenames)

- **`app.py`** — `GenLauncherApp(App)` owns `mod_service`, `options_service`, `repo_service` as instance attributes. Screens access them via `self.app.mod_service` (requires `app` property override for type safety).
- **`config.py`** — hardcoded repo URLs (ZH YAML, Gen YAML), modded EXE download link, GenTool download link.
- **`services/s3_service.py`** — AWS Signature V4 HMAC-SHA256 for MinIO auth. Credentials hardcoded (`GEN_INS_A_PKEY`, `GEN_INS_A_SKEY`). URL-encodes slashes as `%2F` in Canonical Query String via `urlencode(quote_via=...)`.
- **`logging_setup.py`** — RotatingFileHandler (1 MB, 3 backups), timestamped filenames (`genlauncher_YYYYMMDD_HHMMSS.log`), root logger at WARNING to silence httpx noise.
- **Screens** (`screens/`): `HomeScreen` (main mod table + actions), `AddModScreen` (repo browser), `OptionsScreen` (install method + Steam path), `CreditsScreen`, `HelpScreen`.
- **Widgets** (`widgets/`): `ModActionPanel` (download/install/uninstall buttons), `StatusPanel` (GenTool/modded launcher/game path), `KeyHints` (keyboard shortcut legend).
- **Styles** (`styles/`): `app.tcss` — Textual CSS for the entire UI.
- **Data models** (`models/`): `Mod`, `ModData` (extends `ModificationReposVersion`), `LauncherOptions`, `InstallationStatus`.

## Workflow

- Before starting a new feature, check `git status` and `git diff` for uncommitted changes. If they exist, commit them with a descriptive message before proceeding to the new feature. Create a todo for the new feature.

## Conventions

- Use `from __future__ import annotations` at top of every file.
- DO NOT add comments unless the user explicitly asks.
- Use `Optional[X]` or `X | None` consistently — pyrightconfig has `typeCheckingMode: basic`.
- Screens needing to access app services must define a typed `app` property override using `TYPE_CHECKING` (see `screens/home_screen.py` for the pattern).
- S3 service uses `_signed_get()` wrapper — never call `self._client.get()` directly for S3 URLs.

## Testing

- 125 tests across 6 files: `test_models.py`, `test_services.py`, `test_ui.py`, `test_entry_point.py`, `test_image_service.py`, `test_thumbnail_widget.py`.
- Run targeted suites during iteration (e.g. `tests/test_thumbnail_widget.py`), full suite only before commits.
- `conftest.py` patches `SteamService.get_mod_dir` to a temp dir for every test — tests never touch real user data.
- `test_download_and_install_full_flow` is the slowest (actual S3 HTTP + file I/O).
- Archive extraction tests (`test_extract_7z_bad_file`, `test_extract_rar_bad_file`) require `py7zr` / `rarfile` from `[archive]` extras.

## Logs

- Log directory: `platformdirs.user_log_dir("genlauncher")` → Linux: `~/.local/state/genlauncher/log/`
- RotatingFileHandler (1 MB, 3 backups), root logger at WARNING to silence httpx noise.
- Filenames: `genlauncher_YYYYMMDD_HHMMSS.log`

## Gotchas

- S3 MinIO port in host → `http://` scheme; no port → `https://`. Logic in `s3_service.py:45-48`.
- `install_mod` expects `ensure_gentool_installed` to have been called beforehand. `_ensure_modded_launcher_installed` is called inside `install_mod` before copying files.
- Only one mod can be installed at a time (C# parity guard in `mod_service.py`).
- Contra S3 files have `!ContraXBeta2_` prefix — `fix_mod_filename` does NOT strip it, only swaps `.gib`→`.big`.
- End-to-end Contra download+install+launch requires Steam + Zero Hour installed (not present on build machine).
- `download_mod` wraps its body in try/except BaseException to reset `mod.downloading` on failure — do not remove.
