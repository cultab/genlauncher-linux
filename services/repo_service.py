from __future__ import annotations

from typing import Optional

import httpx
import yaml

from genlauncher_tui.config import CONFIG
from genlauncher_tui.models.enums import GameType
from genlauncher_tui.models.repo import ReposModsData


class RepoService:
    def __init__(self):
        self._cache: Optional[ReposModsData] = None

    def get_repo_url(self) -> str:
        return CONFIG["repos"]["ZH"]

    async def fetch_repo_data(self) -> ReposModsData:
        if self._cache is not None:
            return self._cache
        url = self.get_repo_url()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        raw = yaml.safe_load(resp.text)
        data = ReposModsData(
            launcher_version=raw.get("LauncherVersion", ""),
            download_link=raw.get("DownloadLink", ""),
            vulkan_repos_data=raw.get("VulkanReposData", ""),
        )
        for entry in raw.get("modDatas", []):
            from genlauncher_tui.models.repo import ModAddonsAndPatches
            m = ModAddonsAndPatches(
                mod_id=entry.get("ModId", 0),
                mod_name=entry.get("ModName", ""),
                mod_link=entry.get("ModLink", ""),
                mod_patches=entry.get("ModPatches", []),
                mod_addons=entry.get("ModAddons", []),
            )
            if data.mod_datas is not None:
                data.mod_datas.append(m)
        data.global_addons_data = raw.get("globalAddonsData", [])
        data.original_game_addons = raw.get("originalGameAddons", [])
        data.original_game_patches = raw.get("originalGamePatches", [])
        for adv in raw.get("AdvData", []):
            from genlauncher_tui.models.repo import AdvertisingData
            if data.adv_data is not None:
                data.adv_data.append(AdvertisingData(
                    mod_name=adv.get("ModName", ""),
                    mod_link=adv.get("ModLink", ""),
                    images_data=adv.get("ImagesData", []),
                ))
        if data.mod_datas is not None:
            data.mod_datas.sort(key=lambda x: x.mod_name or "")
        self._cache = data
        return data
