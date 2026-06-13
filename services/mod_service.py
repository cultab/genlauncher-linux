from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from typing import Optional

import httpx
import yaml

from genlauncher_tui.config import CONFIG
from genlauncher_tui.models.enums import InstallMethod, ModificationType
from genlauncher_tui.models.mod import (
    Mod,
    ModData,
    ModDownloadProgress,
    clean_string,
    fix_mod_filename,
    standard_mod_name,
)
from genlauncher_tui.models.options import InstallationStatus
from genlauncher_tui.models.repo import ReposModsData
from genlauncher_tui.services.download_manager import (
    download_bytes,
    download_file,
    extract_archive,
    get_all_files_recursively,
    get_md5,
    get_total_size,
)
from genlauncher_tui.services.steam_service import SteamService

MODLIST_FILE = "genlauncher_modlist.json"
BACKUP_DIR = "OriginalGameFiles"


def _parse_download_link(link: str) -> str:
    if "dropbox.com" in link:
        return link.replace("?dl=0", "?dl=1")
    if "onedrive.live.com" in link:
        if "embed" in link:
            return link.replace("embed", "download")
        parts = link.replace("https://onedrive.live.com/?", "").split("&")
        cid = ""
        authkey = ""
        resid = ""
        for p in parts:
            if p.startswith("cid="):
                cid = p[4:]
            elif p.startswith("authkey="):
                authkey = p[8:]
            elif p.startswith("id="):
                resid = p[3:]
        return f"https://onedrive.live.com/download?cid={cid}&resid={resid}&authkey={authkey}"
    return link


def _find_file_recursively(folder: str, target: str) -> Optional[str]:
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower() == target.lower():
                return os.path.join(root, f)
    return None


logger = logging.getLogger(__name__)


class ModService:
    def __init__(self, repo_data: Optional[ReposModsData] = None):
        self._repo_data: Optional[ReposModsData] = repo_data
        self._added_mods: list[Mod] = []
        self._download_progress: dict[str, ModDownloadProgress] = {}
        self._lock = asyncio.Lock()
        self._read_mod_list()

    # --- Mod list persistence ---

    def _get_mod_dir(self) -> str:
        return SteamService.get_mod_dir()

    def _modlist_path(self) -> str:
        p = os.path.join(self._get_mod_dir(), MODLIST_FILE)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p

    def _read_mod_list(self):
        path = self._modlist_path()
        if os.path.isfile(path):
            with open(path) as f:
                raw = json.load(f)
            self._added_mods = []
            for entry in raw:
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
                    from genlauncher_tui.models.repo import ModAddonsAndPatches
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
                        s3_host_link=md.get("s3_host_link"),
                        s3_bucket_name=md.get("s3_bucket_name"),
                        s3_folder_name=md.get("s3_folder_name"),
                        s3_host_public_key=md.get("s3_host_public_key"),
                        s3_host_secret_key=md.get("s3_host_secret_key"),
                    )
                self._added_mods.append(m)
        else:
            self._added_mods = []
            self._write_mod_list()

    def _write_mod_list(self):
        raw = []
        for m in self._added_mods:
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
                    "s3_host_link": m.mod_data.s3_host_link,
                    "s3_bucket_name": m.mod_data.s3_bucket_name,
                    "s3_folder_name": m.mod_data.s3_folder_name,
                    "s3_host_public_key": m.mod_data.s3_host_public_key,
                    "s3_host_secret_key": m.mod_data.s3_host_secret_key,
                }
            raw.append(entry)
        with open(self._modlist_path(), "w") as f:
            json.dump(raw, f, indent=2)

    # --- Repo data ---

    def set_repo_data(self, data: ReposModsData):
        self._repo_data = data

    async def _ensure_mod_data(self, mod: Mod):
        if mod.mod_data is None and mod.mod_info and mod.mod_info.mod_link:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(mod.mod_info.mod_link)
                resp.raise_for_status()
            raw = yaml.safe_load(resp.text)
            if raw:
                mod.mod_data = _yaml_to_mod_data(raw)
            else:
                mod.mod_data = ModData()

    # --- Public API ---

    def get_added_mods(self) -> list[Mod]:
        return self._added_mods

    def get_unadded_mods(self) -> ReposModsData:
        if not self._repo_data:
            return ReposModsData()
        added_names = {m.mod_info.mod_name.lower() for m in self._added_mods if m.mod_info}
        unadded = ReposModsData()
        unadded_datas = unadded.mod_datas
        assert unadded_datas is not None
        for entry in (self._repo_data.mod_datas or []):
            if entry.mod_name.lower() not in added_names:
                unadded_datas.append(entry)
        unadded.global_addons_data = self._repo_data.global_addons_data
        unadded.original_game_addons = self._repo_data.original_game_addons
        unadded.original_game_patches = self._repo_data.original_game_patches
        unadded.adv_data = self._repo_data.adv_data
        return unadded

    def add_mod_to_list(self, mod_name: str) -> bool:
        if not self._repo_data:
            return False
        match = None
        for entry in (self._repo_data.mod_datas or []):
            if entry.mod_name.strip().lower() == mod_name.strip().lower():
                match = entry
                break
        if not match:
            return False
        if any(m.mod_info and m.mod_info.mod_name == match.mod_name for m in self._added_mods):
            return False
        self._added_mods.append(Mod(mod_info=match))
        self._write_mod_list()
        return True

    def remove_mod_from_list(self, mod_name: str) -> bool:
        for i, m in enumerate(self._added_mods):
            if m.mod_info and m.mod_info.mod_name == mod_name and not m.installed:
                self._added_mods.pop(i)
                self._write_mod_list()
                return True
        return False

    def get_download_progress(self, mod_name: str) -> ModDownloadProgress:
        key = standard_mod_name(mod_name)
        if key in self._download_progress:
            p = self._download_progress[key]
            if p.downloaded:
                del self._download_progress[key]
            return p
        return ModDownloadProgress()

    async def download_mod(self, mod_name: str):
        async with self._lock:
            mod = None
            for m in self._added_mods:
                if m.mod_info and m.mod_info.mod_name.strip().lower() == mod_name.strip().lower():
                    mod = m
                    break
            if not mod:
                raise ValueError(f"Mod not found: {mod_name}")
            await self._ensure_mod_data(mod)
            mod.downloading = True
            self._write_mod_list()

        try:
            cleaned = mod.cleaned_mod_name
            mod_dir = os.path.join(self._get_mod_dir(), cleaned)
            os.makedirs(mod_dir, exist_ok=True)
            installed_files: list[str] = []
            total_install_size = 0

            if mod.has_s3_storage():
                from genlauncher_tui.services.s3_service import S3StorageService
                s3 = S3StorageService()
                try:
                    file_list = await s3.get_mod_files(mod)
                    total_size = sum(f.size for f in file_list)
                    self._create_s3_progress(total_size, file_list, cleaned)
                    for f in file_list:
                        self._download_progress[standard_mod_name(cleaned)].current_file = f.file_name
                        file_path = os.path.join(mod_dir, f.file_name)
                        if os.path.isfile(file_path):
                            if get_md5(file_path) == f.hash.lower():
                                files_list = self._download_progress[standard_mod_name(cleaned)].downloaded_files
                                if files_list is not None:
                                    files_list.append(f.file_name)
                                self._download_progress[standard_mod_name(cleaned)].downloaded_size += f.size
                                total_install_size += f.size
                                continue
                            os.unlink(file_path)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        data = await s3.download_s3_file(f.file_name, mod)
                        with open(file_path, "wb") as fh:
                            fh.write(data)
                        if get_md5(file_path) == f.hash.lower():
                            installed_files.append(f.file_name)
                            files_list = self._download_progress[standard_mod_name(cleaned)].downloaded_files
                            if files_list is not None:
                                files_list.append(f.file_name)
                            total_install_size += f.size
                            self._download_progress[standard_mod_name(cleaned)].downloaded_size += f.size
                        else:
                            if "changelog" not in file_path.lower() and os.path.splitext(file_path)[1].lower() != ".txt":
                                raise RuntimeError(f"Hash mismatch for {f.file_name}")
                    self._download_progress[standard_mod_name(cleaned)].downloaded = True
                finally:
                    await s3.close()
            else:
                md = mod.mod_data
                dl_link = (md.simple_download_link or "") if md else ""
                link = _parse_download_link(dl_link)
                key = standard_mod_name(cleaned)
                self._create_simple_progress(mod_name, 0)
                self._download_progress[key].current_file = os.path.basename(link)

                def _progress(downloaded: int, total: int):
                    p = self._download_progress.get(key)
                    if p:
                        p.total_download_size = total
                        p.downloaded_size = downloaded

                data, content_type = await download_bytes(link, progress_callback=_progress)
                total_size = len(data)
                self._download_progress[key].total_download_size = total_size
                self._download_progress[key].downloaded_size = total_size

                ext = _mime_to_ext(content_type)
                if not ext:
                    ext = ".zip"
                archive_path = os.path.join(mod_dir, cleaned + ext)
                with open(archive_path, "wb") as fh:
                    fh.write(data)
                self._download_progress[standard_mod_name(cleaned)].downloaded_size = total_size

                extract_archive(archive_path, mod_dir)
                installed_files = get_all_files_recursively(mod_dir)
                installed_files = [os.path.relpath(f, mod_dir) for f in installed_files]
                total_install_size = get_total_size([os.path.join(mod_dir, f) for f in installed_files])
                self._download_progress[standard_mod_name(cleaned)].downloaded = True
                self._download_progress[standard_mod_name(cleaned)].downloaded_files = list(installed_files)
                self._download_progress[standard_mod_name(cleaned)].downloaded_size = total_install_size

            async with self._lock:
                mod.downloading = False
                mod.downloaded = True
                mod.downloaded_version = mod.mod_data.version if mod.mod_data else ""
                mod.downloaded_files = installed_files
                mod.total_size = total_install_size
                mod.mod_dir = mod_dir
                self._write_mod_list()
        except BaseException:
            async with self._lock:
                mod.downloading = False
                self._write_mod_list()
            raise

    def _create_s3_progress(self, total_size: int, file_list: list, cleaned: str):
        key = standard_mod_name(cleaned)
        self._download_progress[key] = ModDownloadProgress(
            total_download_size=total_size,
            file_list=[f.file_name for f in file_list],
            downloaded_files=[],
            downloaded_size=0,
            downloaded=False,
        )

    def _create_simple_progress(self, mod_name: str, total_size: int):
        key = standard_mod_name(mod_name)
        self._download_progress[key] = ModDownloadProgress(
            total_download_size=total_size,
            file_list=[],
            downloaded_files=[],
            downloaded_size=0,
            downloaded=False,
        )

    def install_mod(self, mod_name: str, install_method: InstallMethod):
        mod = None
        for m in self._added_mods:
            if m.mod_info and m.mod_info.mod_name == mod_name:
                mod = m
                break
        if not mod:
            raise ValueError(f"Mod not found: {mod_name}")

        if any(m.installed and m.mod_info and m.mod_info.mod_name != mod_name for m in self._added_mods):
            raise RuntimeError("Another mod is already installed. Uninstall it first.")

        self._ensure_modded_launcher_installed(install_method)
        game_dir = SteamService.get_game_install_dir()
        mod_folder = mod.mod_dir
        if not mod_folder or not os.path.isdir(mod_folder):
            raise FileNotFoundError(f"Mod folder not found: {mod_folder}")

        for mod_file in (mod.downloaded_files or []):
            name = fix_mod_filename(mod_file)
            src = os.path.join(mod_folder, mod_file)
            dst = os.path.join(game_dir, name)
            if os.path.isfile(dst):
                self._backup_original(dst)
            if install_method == InstallMethod.SymLink:
                from genlauncher_tui.services.symlink_service import SymLinkService
                SymLinkService.create_symlink(dst, src)
            else:
                shutil.copy2(src, dst)

        for mod_file in (mod.downloaded_files or []):
            name = fix_mod_filename(mod_file)
            dst = os.path.join(game_dir, name)
            if not os.path.isfile(dst):
                raise RuntimeError(f"Installation failed: {dst} not found")

        mod.installed = True
        self._write_mod_list()
        self._ensure_modded_launcher_installed(install_method)

    def uninstall_mod(self, mod_name: str):
        mod = None
        for m in self._added_mods:
            if m.mod_info and m.mod_info.mod_name == mod_name:
                mod = m
                break
        if not mod:
            return
        game_dir = SteamService.get_game_install_dir()
        for mod_file in (mod.downloaded_files or []):
            name = fix_mod_filename(mod_file)
            game_path = os.path.join(game_dir, name)
            if not self._restore_original(mod_file):
                if os.path.isfile(game_path):
                    os.unlink(game_path)
        mod.installed = False
        self._write_mod_list()

    def delete_mod(self, mod_name: str):
        mod = None
        for m in self._added_mods:
            if m.mod_info and m.mod_info.mod_name == mod_name:
                mod = m
                break
        if not mod:
            return
        mod.downloaded = False
        mod.downloaded_version = ""
        mod.installed = False
        if mod.mod_dir and os.path.isdir(mod.mod_dir):
            shutil.rmtree(mod.mod_dir, ignore_errors=True)
        mod.downloaded_files = None
        mod.total_size = 0
        mod.mod_dir = None
        self._write_mod_list()

    def get_installation_status(self) -> InstallationStatus:
        try:
            ml = self._check_modded_launcher_installed()
        except Exception:
            logger.warning("Could not check modded launcher status", exc_info=True)
            ml = False
        try:
            gt = self._check_gentool_installed()
        except Exception:
            logger.warning("Could not check GenTool status", exc_info=True)
            gt = False
        return InstallationStatus(modded_launcher=ml, gen_tool=gt)

    def _check_modded_launcher_installed(self) -> bool:
        game_dir = SteamService.get_game_install_dir()
        game_exe = os.path.join(game_dir, "Generals.exe")
        if os.path.isfile(game_exe):
            modded_exe = os.path.join(self._get_mod_dir(), "ModdedLauncher", "modded.exe")
            if os.path.isfile(modded_exe) and get_md5(game_exe) == get_md5(modded_exe):
                return True
        return False

    def _ensure_modded_launcher_installed(self, install_method: InstallMethod):
        game_dir = SteamService.get_game_install_dir()
        game_exe = os.path.join(game_dir, "Generals.exe")
        modded_dir = os.path.join(self._get_mod_dir(), "ModdedLauncher")
        modded_exe = os.path.join(modded_dir, "modded.exe")

        if os.path.isfile(game_exe):
            if os.path.isfile(modded_exe) and get_md5(game_exe) == get_md5(modded_exe):
                return
            self._backup_original("Generals.exe")

        if not os.path.isfile(modded_exe):
            self._download_modded_exe(modded_exe)

        if os.path.isfile(modded_exe):
            if install_method == InstallMethod.SymLink:
                from genlauncher_tui.services.symlink_service import SymLinkService
                SymLinkService.create_symlink(game_exe, modded_exe)
            else:
                shutil.copy2(modded_exe, game_exe)

    def _download_modded_exe(self, dest: str):
        url = CONFIG["extra"]["modded_exe_download_link"]
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        import httpx as hx
        resp = hx.get(url)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)

    def _check_gentool_installed(self) -> bool:
        expected_hash = CONFIG["extra"]["gentool_dll_hash"]
        dll_path = os.path.join(SteamService.get_game_install_dir(), "d3d8.dll")
        if os.path.isfile(dll_path):
            return get_md5(dll_path) == expected_hash
        return False

    async def ensure_gentool_installed(self, install_method: InstallMethod):
        game_dir = SteamService.get_game_install_dir()
        dll_path = os.path.join(game_dir, "d3d8.dll")
        if os.path.isfile(dll_path) and self._check_gentool_installed():
            return
        self._backup_original("d3d8.dll")
        gentool_dir = os.path.join(self._get_mod_dir(), "GenTool")
        os.makedirs(gentool_dir, exist_ok=True)
        zip_path = os.path.join(gentool_dir, "gentool.zip")
        url = CONFIG["extra"]["gentool_download_link"]
        await download_file(url, zip_path)
        extract_archive(zip_path, gentool_dir)
        found = _find_file_recursively(gentool_dir, "d3d8.dll")
        if found:
            if install_method == InstallMethod.SymLink:
                from genlauncher_tui.services.symlink_service import SymLinkService
                SymLinkService.create_symlink(dll_path, found)
            else:
                shutil.copy2(found, dll_path)

    def _backup_original(self, filename: str):
        game_dir = SteamService.get_game_install_dir()
        backup_dir = os.path.join(self._get_mod_dir(), BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
        src = os.path.join(game_dir, filename) if not os.path.isabs(filename) else filename
        dst = os.path.join(backup_dir, filename) if not os.path.isabs(filename) else os.path.join(backup_dir, os.path.basename(filename))
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)

    def _restore_original(self, filename: str) -> bool:
        game_dir = SteamService.get_game_install_dir()
        backup_dir = os.path.join(self._get_mod_dir(), BACKUP_DIR)
        backup_file = os.path.join(backup_dir, filename)
        game_file = os.path.join(game_dir, filename)
        if os.path.isfile(backup_file):
            shutil.move(backup_file, game_file)
            return True
        return False


def _yaml_to_mod_data(raw: dict) -> ModData:
    return ModData(
        modification_type=ModificationType(raw["ModificationType"]) if "ModificationType" in raw else ModificationType.Mod,
        name=raw.get("Name", ""),
        version=raw.get("Version", ""),
        simple_download_link=raw.get("SimpleDownloadLink"),
        ui_image_source_link=raw.get("UIImageSourceLink"),
        discord_link=raw.get("DiscordLink"),
        mod_db_link=raw.get("ModDBLink"),
        news_link=raw.get("NewsLink"),
        dependence_name=raw.get("DependenceName"),
        s3_host_link=raw.get("S3HostLink"),
        s3_bucket_name=raw.get("S3BucketName"),
        s3_folder_name=raw.get("S3FolderName"),
        s3_host_public_key=raw.get("S3HostPublicKey"),
        s3_host_secret_key=raw.get("S3HostSecretKey"),
        network_info=raw.get("NetworkInfo"),
        deprecated=raw.get("Deprecated", False),
        support_link=raw.get("SupportLink"),
    )


_MIME_EXT_MAP = {
    "application/zip": ".zip",
    "application/x-7z-compressed": ".7z",
    "application/x-rar-compressed": ".rar",
    "application/gzip": ".gz",
    "application/x-tar": ".tar",
    "application/x-bzip2": ".bz2",
    "application/x-lzip": ".lz",
    "application/x-xz": ".xz",
}


def _mime_to_ext(mime: str) -> str:
    for k, v in _MIME_EXT_MAP.items():
        if k in mime:
            return v
    if "7z" in mime or "7-zip" in mime:
        return ".7z"
    if "rar" in mime:
        return ".rar"
    if "zip" in mime:
        return ".zip"
    return ".zip"
