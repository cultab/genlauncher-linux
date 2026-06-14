from __future__ import annotations

import os
import platform
import re
from pathlib import Path
from typing import Optional

from genlauncher_tui.models.enums import GameType

ZERO_HOUR_GAME_ID = "2732960"


class SteamService:
    @staticmethod
    def detect_platform() -> str:
        system = platform.system()
        if system == "Windows":
            return "Windows"
        elif system == "Darwin":
            return "Mac"
        elif system == "Linux":
            return "Linux"
        raise OSError("Unsupported platform")

    @staticmethod
    def get_default_steam_path() -> str:
        plat = SteamService.detect_platform()
        home = str(Path.home())
        if plat == "Windows":
            return r"C:\Program Files (x86)\Steam"
        elif plat == "Mac":
            return os.path.join(home, "Library", "Application Support", "Steam")
        else:
            path = os.path.join(home, ".steam", "steam")
            if not os.path.isdir(path):
                flatpak = os.path.join(home, ".var", "app", "com.valvesoftware.Steam", "data", "Steam")
                if os.path.isdir(flatpak):
                    path = flatpak
            return path

    @staticmethod
    def get_library_paths(library_folders_path: str) -> list[str]:
        paths = []
        regex = re.compile(r'"path"\s+"(.*?)"')
        with open(library_folders_path) as f:
            for line in f:
                m = regex.search(line)
                if m:
                    paths.append(m.group(1).replace("\\\\", "\\"))
        lib_dir = os.path.dirname(os.path.dirname(library_folders_path))
        if lib_dir not in paths:
            paths.append(lib_dir)
        return paths

    @staticmethod
    def get_steam_install_path() -> str:
        steam_path = SteamService.get_default_steam_path()
        library_folders_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
        if not os.path.isfile(library_folders_path):
            raise FileNotFoundError(f"libraryfolders.vdf not found at {library_folders_path}")
        library_paths = SteamService.get_library_paths(library_folders_path)
        for lib_path in library_paths:
            acf = os.path.join(lib_path, "steamapps", f"appmanifest_{ZERO_HOUR_GAME_ID}.acf")
            if os.path.isfile(acf):
                return os.path.join(lib_path, "steamapps", "common")
        raise FileNotFoundError("Zero Hour game installation not found in any Steam library")

    @staticmethod
    def get_generals_install_dir(steam_install_path: Optional[str] = None) -> str:
        if steam_install_path is None:
            steam_install_path = SteamService.get_steam_install_path()
        return os.path.join(steam_install_path, "Command and Conquer Generals")

    @staticmethod
    def get_zero_hour_install_dir(steam_install_path: Optional[str] = None) -> str:
        if steam_install_path is None:
            steam_install_path = SteamService.get_steam_install_path()
        return os.path.join(steam_install_path, "Command & Conquer Generals - Zero Hour")

    @staticmethod
    def get_game_install_dir() -> str:
        return SteamService.get_zero_hour_install_dir()

    @staticmethod
    def get_game() -> GameType:
        return GameType.ZH

    @staticmethod
    def get_common_folder() -> str:
        return SteamService.get_steam_install_path()

    @staticmethod
    def create_mods_folder():
        install_dir = SteamService.get_generals_install_dir()
        mods_dir = os.path.join(install_dir, "_mods")
        os.makedirs(mods_dir, exist_ok=True)

    @staticmethod
    def get_mod_dir() -> str:
        data_home = os.environ.get("XDG_DATA_HOME", os.path.join(str(Path.home()), ".local", "share"))
        return os.path.join(data_home, "genlauncher")

    @staticmethod
    def get_steam_userdata_dir() -> str:
        steam_path = SteamService.get_default_steam_path()
        return os.path.join(os.path.dirname(steam_path), "userdata")
