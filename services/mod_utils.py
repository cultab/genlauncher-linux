"""Pure utility functions for mod operations — no state, no side effects beyond I/O."""
from __future__ import annotations

import os
from typing import Optional

from genlauncher_tui.models.enums import ModificationType
from genlauncher_tui.models.mod import ModData

MODLIST_FILE = "genlauncher_modlist.json"
BACKUP_DIR = "OriginalGameFiles"

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


def parse_download_link(link: str) -> str:
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


def find_file_recursively(folder: str, target: str) -> Optional[str]:
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower() == target.lower():
                return os.path.join(root, f)
    return None


def yaml_to_mod_data(raw: dict) -> ModData:
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


def mime_to_ext(mime: str) -> str:
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
