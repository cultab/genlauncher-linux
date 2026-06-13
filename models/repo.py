from __future__ import annotations

import dataclasses
from typing import Optional


@dataclasses.dataclass
class ModAddonsAndPatches:
    mod_id: int = 0
    mod_name: str = ""
    mod_link: str = ""
    mod_patches: Optional[list[str]] = None
    mod_addons: Optional[list[str]] = None

    def __post_init__(self):
        if self.mod_patches is None:
            self.mod_patches = []
        if self.mod_addons is None:
            self.mod_addons = []


@dataclasses.dataclass
class AdvertisingData:
    mod_name: str = ""
    mod_link: str = ""
    images_data: Optional[list[str]] = None

    def __post_init__(self):
        if self.images_data is None:
            self.images_data = []


@dataclasses.dataclass
class ReposModsData:
    launcher_version: str = ""
    download_link: str = ""
    vulkan_repos_data: str = ""
    mod_datas: Optional[list[ModAddonsAndPatches]] = None
    global_addons_data: Optional[list[str]] = None
    original_game_addons: Optional[list[str]] = None
    original_game_patches: Optional[list[str]] = None
    adv_data: Optional[list[AdvertisingData]] = None

    def __post_init__(self):
        if self.mod_datas is None:
            self.mod_datas = []
        if self.global_addons_data is None:
            self.global_addons_data = []
        if self.original_game_addons is None:
            self.original_game_addons = []
        if self.original_game_patches is None:
            self.original_game_patches = []
        if self.adv_data is None:
            self.adv_data = []
