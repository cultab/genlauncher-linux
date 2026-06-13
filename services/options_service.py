from __future__ import annotations

import json
import logging
import os

from platformdirs import user_config_dir

from genlauncher_tui.models.enums import InstallMethod
from genlauncher_tui.models.options import LauncherOptions
from genlauncher_tui.services.steam_service import SteamService
from genlauncher_tui.services.symlink_service import SymLinkService

OPTIONS_FILENAME = "genlauncher_options.json"


logger = logging.getLogger(__name__)


class OptionsService:
    def __init__(self):
        self._options: LauncherOptions | None = None

    @staticmethod
    def get_app_data_folder() -> str:
        folder = user_config_dir("genlauncher", ensure_exists=True)
        return folder

    @staticmethod
    def get_app_data_file() -> str:
        return os.path.join(OptionsService.get_app_data_folder(), OPTIONS_FILENAME)

    def _read_options(self):
        self._migrate_old_location()
        path = self.get_app_data_file()
        if os.path.isfile(path):
            with open(path) as f:
                data = json.load(f)
            self._options = LauncherOptions(
                install_method=InstallMethod(data.get("install_method", InstallMethod.CopyFiles.value)),
                steam_path=data.get("steam_path", ""),
            )
            self._fix_options()
            self._write_options()
        else:
            self._options = self._default_settings()
            self._fix_options()
            self._write_options()

    def _write_options(self):
        path = self.get_app_data_file()
        opts = self._options
        if opts is None:
            opts = self._default_settings()
        with open(path, "w") as f:
            json.dump({
                "install_method": opts.install_method.value,
                "steam_path": opts.steam_path,
            }, f, indent=2)

    def _fix_options(self):
        opts = self._options
        if opts is None:
            return
        if opts.install_method == InstallMethod.SymLink and not SymLinkService.is_symlinks_supported():
            opts.install_method = InstallMethod.CopyFiles
        if not opts.steam_path:
            try:
                opts.steam_path = SteamService.get_steam_install_path()
            except Exception:
                logger.warning("Could not auto-detect Steam path", exc_info=True)

    @staticmethod
    def _default_settings() -> LauncherOptions:
        method = InstallMethod.SymLink if SymLinkService.is_symlinks_supported() else InstallMethod.CopyFiles
        steam_path = ""
        try:
            steam_path = SteamService.get_steam_install_path()
        except Exception:
            logger.warning("Could not detect default Steam path", exc_info=True)
        return LauncherOptions(install_method=method, steam_path=steam_path)

    @staticmethod
    def _migrate_old_location():
        try:
            old_dir = SteamService.get_game_install_dir()
            old_file = os.path.join(old_dir, OPTIONS_FILENAME)
            if os.path.isfile(old_file):
                import shutil
                shutil.move(old_file, OptionsService.get_app_data_file())
        except Exception:
            logger.warning("Failed to migrate old options location", exc_info=True)

    def get_options(self) -> LauncherOptions:
        if self._options is None:
            self._read_options()
            if self._options is None:
                self._options = self._default_settings()
        return self._options

    def set_options(self, opts: LauncherOptions) -> LauncherOptions:
        self._options = opts
        self._fix_options()
        self._write_options()
        return self._options

    def reset_options(self) -> LauncherOptions:
        self._options = self._default_settings()
        self._fix_options()
        self._write_options()
        return self._options
