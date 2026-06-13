from __future__ import annotations

import dataclasses
import re
from typing import Optional

import httpx

from genlauncher_tui.models.mod import Mod

GEN_INS_A_PKEY = "S58TYR9ISEZV8PBP8QG1"
GEN_INS_A_SKEY = "b2RU1oqVU5toJRnb4gODrXX8sBSgoLcHRX6qPWxj"


@dataclasses.dataclass
class ModificationFileInfo:
    file_name: str
    hash: str
    size: int

    def __eq__(self, other):
        if not isinstance(other, ModificationFileInfo):
            return NotImplemented
        if self.hash.lower() != other.hash.lower():
            return False
        if self.file_name.lower() == other.file_name.lower():
            return True
        base1 = re.sub(r"\.[^.]+$", "", self.file_name)
        base2 = re.sub(r"\.[^.]+$", "", other.file_name)
        return base1.lower() == base2.lower()

    def __hash__(self):
        return hash((self.file_name.upper(), self.hash.upper()))


class S3StorageService:
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=120.0)

    async def get_mod_files(self, mod: Mod) -> list[ModificationFileInfo]:
        md = mod.mod_data
        if not md:
            return []
        key = (md.s3_host_public_key or GEN_INS_A_PKEY).strip()
        secret = (md.s3_host_secret_key or GEN_INS_A_SKEY).strip()
        host = md.s3_host_link or ""
        bucket = md.s3_bucket_name or ""
        folder = md.s3_folder_name or ""

        host_part = host.split(":")[0]
        list_url = f"https://{host_part}/{bucket}/?prefix={folder}/"
        resp = await self._client.get(list_url)
        resp.raise_for_status()

        files = []
        text = resp.text
        for match in re.finditer(r"<Key>(.*?)</Key>\s*<Size>(\d+)</Size>\s*<ETag>\"(.*?)\"</ETag>", text, re.DOTALL):
            key_name = match.group(1)
            size = int(match.group(2))
            etag = match.group(3)
            rel_path = key_name.replace(folder + "/", "", 1) if folder else key_name
            if not rel_path:
                continue
            files.append(ModificationFileInfo(
                file_name=rel_path,
                hash=etag.replace('"', ""),
                size=size,
            ))

        if not files:
            listing_url = f"https://{host_part}/{bucket}/{folder}/"
            resp2 = await self._client.get(listing_url)
            resp2.raise_for_status()
            text2 = resp2.text
            for match in re.finditer(r"<Key>(.*?)</Key>\s*<Size>(\d+)</Size>\s*<ETag>\"(.*?)\"</ETag>", text2, re.DOTALL):
                key_name = match.group(1)
                size = int(match.group(2))
                etag = match.group(3)
                rel_path = key_name.replace(folder + "/", "", 1) if folder else key_name
                if not rel_path:
                    continue
                files.append(ModificationFileInfo(
                    file_name=rel_path,
                    hash=etag.replace('"', ""),
                    size=size,
                ))

        return files

    async def download_s3_file(self, filename: str, mod: Mod) -> bytes:
        md = mod.mod_data
        if not md:
            raise ValueError("No mod data")
        host = (md.s3_host_link or "").split(":")[0]
        bucket = md.s3_bucket_name or ""
        folder = md.s3_folder_name or ""
        url = f"https://{host}/{bucket}/{folder}/{filename}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.content

    async def close(self):
        await self._client.aclose()
