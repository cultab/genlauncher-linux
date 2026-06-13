from __future__ import annotations

import dataclasses
import re
from typing import TYPE_CHECKING, Optional

from .enums import ModificationType

if TYPE_CHECKING:
    from .repo import ModAddonsAndPatches


@dataclasses.dataclass
class ModificationReposVersion:
    modification_type: ModificationType = ModificationType.Mod
    name: str = ""
    version: str = ""
    simple_download_link: Optional[str] = None
    ui_image_source_link: Optional[str] = None
    discord_link: Optional[str] = None
    mod_db_link: Optional[str] = None
    news_link: Optional[str] = None
    dependence_name: Optional[str] = None
    s3_host_link: Optional[str] = None
    s3_bucket_name: Optional[str] = None
    s3_folder_name: Optional[str] = None
    s3_host_public_key: Optional[str] = None
    s3_host_secret_key: Optional[str] = None
    network_info: Optional[str] = None
    deprecated: bool = False
    support_link: Optional[str] = None

    def __eq__(self, other):
        if not isinstance(other, ModificationReposVersion):
            return NotImplemented
        return self.name.lower() == other.name.lower()

    def __hash__(self):
        return hash(self.name.lower())

    def __str__(self):
        return self.name


@dataclasses.dataclass
class ModData(ModificationReposVersion):
    is_selected: bool = False
    installed: bool = False

    def __eq__(self, other):
        if not isinstance(other, ModData):
            return NotImplemented
        return (self.name + self.version).lower() == (other.name + other.version).lower()

    def __hash__(self):
        return hash((self.name + self.version).lower())

    def compare_to(self, other: ModData) -> int:
        self_digits = "".join(c for c in self.version if c.isdigit())
        other_digits = "".join(c for c in other.version if c.isdigit())

        while len(self_digits) > len(other_digits):
            other_digits += "0"
        while len(self_digits) < len(other_digits):
            self_digits += "0"

        if not self_digits:
            self_digits = "-1"
        if not other_digits:
            other_digits = "-1"

        return int(self_digits) - int(other_digits)

    def union(self, other: ModData):
        self.is_selected = self.is_selected or other.is_selected
        self.installed = self.installed or other.installed

        if other.simple_download_link and not self.simple_download_link:
            self.simple_download_link = other.simple_download_link
        if other.modification_type != ModificationType.Mod and self.modification_type == ModificationType.Mod:
            self.modification_type = other.modification_type
        if other.ui_image_source_link and not self.ui_image_source_link:
            self.ui_image_source_link = other.ui_image_source_link
        if other.dependence_name and not self.dependence_name:
            self.dependence_name = other.dependence_name
        if other.news_link and not self.news_link:
            self.news_link = other.news_link
        if other.mod_db_link and not self.mod_db_link:
            self.mod_db_link = other.mod_db_link
        if other.discord_link and not self.discord_link:
            self.discord_link = other.discord_link
        if other.network_info and not self.network_info:
            self.network_info = other.network_info
        if other.support_link and not self.support_link:
            self.support_link = other.support_link
        if other.s3_bucket_name and not self.s3_bucket_name:
            self.s3_bucket_name = other.s3_bucket_name
        if other.s3_folder_name and not self.s3_folder_name:
            self.s3_folder_name = other.s3_folder_name
        if other.s3_host_link and not self.s3_host_link:
            self.s3_host_link = other.s3_host_link
        if other.s3_host_public_key and not self.s3_host_public_key:
            self.s3_host_public_key = other.s3_host_public_key
        if other.s3_host_secret_key and not self.s3_host_secret_key:
            self.s3_host_secret_key = other.s3_host_secret_key

        self.deprecated = other.deprecated


@dataclasses.dataclass
class Mod:
    installed: bool = False
    installing: bool = False
    downloading: bool = False
    downloaded: bool = False
    downloaded_version: str = ""
    mod_info: Optional["ModAddonsAndPatches"] = None
    mod_data: Optional[ModData] = None
    mod_dir: Optional[str] = None
    total_size: int = 0
    downloaded_files: Optional[list[str]] = None

    @property
    def cleaned_mod_name(self) -> str:
        return clean_string(self.mod_info.mod_name) if self.mod_info else ""

    def has_s3_storage(self) -> bool:
        md = self.mod_data
        return bool(md and md.s3_host_link and md.s3_folder_name and md.s3_bucket_name)


def clean_string(input_str: str) -> str:
    ascii_only = re.sub(r"[^\x00-\x7F]", "", input_str)
    cleaned = re.sub(r"[^a-zA-Z\s]", "", ascii_only)
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned


def standard_mod_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", name).lower()


def fix_mod_filename(filename: str) -> str:
    if filename.endswith(".gib"):
        filename = filename.replace(".gib", ".big")
    return filename


@dataclasses.dataclass
class ModDownloadProgress:
    total_download_size: int = 0
    downloaded_size: int = 0
    file_list: Optional[list[str]] = None
    downloaded_files: Optional[list[str]] = None
    downloaded: bool = False

    @property
    def percentage(self) -> float:
        if self.total_download_size == 0:
            return 0.0
        return int(self.downloaded_size / self.total_download_size * 100)
