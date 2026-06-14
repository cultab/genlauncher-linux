"""JSON persistence for the mod list — load and save Mod objects."""
from __future__ import annotations

import json
import logging
import os

from genlauncher_tui.models.mod import Mod, ModData
from genlauncher_tui.models.repo import ModAddonsAndPatches
from genlauncher_tui.services.mod_utils import MODLIST_FILE
from genlauncher_tui.services.steam_service import SteamService

logger = logging.getLogger(__name__)


class ModListStore:
    """Handles atomic JSON read/write of the added-mods list."""

    @staticmethod
    def _mod_dir() -> str:
        return SteamService.get_mod_dir()

    def _modlist_path(self) -> str:
        p = os.path.join(self._mod_dir(), MODLIST_FILE)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p

    def load(self) -> list[Mod]:
        path = self._modlist_path()
        added: list[Mod] = []
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    raw = json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupted mod list, starting fresh", exc_info=True)
                self._atomic_write(added)
                return added
            for entry in raw:
                try:
                    m = Mod(
                        installed=entry.get("installed", False),
                        installing=entry.get("installing", False),
                        downloading=entry.get("downloading", False),
                        downloaded=entry.get("downloaded", False),
                        downloaded_version=entry.get("downloaded_version", ""),
                        mod_dir=entry.get("mod_dir"),
                        total_size=entry.get("total_size", 0),
                        downloaded_files=entry.get("downloaded_files"),
                    )
                    mi = entry.get("mod_info")
                    if mi:
                        m.mod_info = ModAddonsAndPatches(
                            mod_id=mi.get("mod_id", 0),
                            mod_name=mi.get("mod_name", ""),
                            mod_link=mi.get("mod_link", ""),
                            mod_patches=mi.get("mod_patches", []),
                            mod_addons=mi.get("mod_addons", []),
                        )
                    md = entry.get("mod_data")
                    if md:
                        m.mod_data = ModData(
                            name=md.get("name", ""),
                            version=md.get("version", ""),
                            simple_download_link=md.get("simple_download_link"),
                            ui_image_source_link=md.get("ui_image_source_link"),
                            s3_host_link=md.get("s3_host_link"),
                            s3_bucket_name=md.get("s3_bucket_name"),
                            s3_folder_name=md.get("s3_folder_name"),
                            s3_host_public_key=md.get("s3_host_public_key"),
                            s3_host_secret_key=md.get("s3_host_secret_key"),
                        )
                    added.append(m)
                except Exception:
                    logger.exception("Skipping bad mod list entry")
        else:
            self._atomic_write(added)
        return added

    def dump(self, mods: list[Mod]) -> None:
        raw = []
        for m in mods:
            entry = {
                "installed": m.installed,
                "installing": m.installing,
                "downloading": m.downloading,
                "downloaded": m.downloaded,
                "downloaded_version": m.downloaded_version,
                "mod_dir": m.mod_dir,
                "total_size": m.total_size,
                "downloaded_files": m.downloaded_files,
            }
            if m.mod_info:
                entry["mod_info"] = {
                    "mod_id": m.mod_info.mod_id,
                    "mod_name": m.mod_info.mod_name,
                    "mod_link": m.mod_info.mod_link,
                    "mod_patches": m.mod_info.mod_patches,
                    "mod_addons": m.mod_info.mod_addons,
                }
            if m.mod_data:
                entry["mod_data"] = {
                    "name": m.mod_data.name,
                    "version": m.mod_data.version,
                    "simple_download_link": m.mod_data.simple_download_link,
                    "ui_image_source_link": m.mod_data.ui_image_source_link,
                    "s3_host_link": m.mod_data.s3_host_link,
                    "s3_bucket_name": m.mod_data.s3_bucket_name,
                    "s3_folder_name": m.mod_data.s3_folder_name,
                    "s3_host_public_key": m.mod_data.s3_host_public_key,
                    "s3_host_secret_key": m.mod_data.s3_host_secret_key,
                }
            raw.append(entry)
        self._atomic_write(raw)

    def _atomic_write(self, raw: list) -> None:
        path = self._modlist_path()
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(raw, f, indent=2)
        os.replace(tmp, path)
