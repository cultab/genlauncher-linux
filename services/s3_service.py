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

    @staticmethod
    def _base_url(host: str) -> str:
        if ":" in host:
            return f"http://{host}"
        return f"https://{host}"

    async def get_mod_files(self, mod: Mod) -> list[ModificationFileInfo]:
        md = mod.mod_data
        if not md:
            return []
        key = (md.s3_host_public_key or GEN_INS_A_PKEY).strip()
        secret = (md.s3_host_secret_key or GEN_INS_A_SKEY).strip()
        host = md.s3_host_link or ""
        bucket = md.s3_bucket_name or ""
        folder = md.s3_folder_name or ""

        base = self._base_url(host)
        list_url = f"{base}/{bucket}/?prefix={folder}/"
        resp = await self._client.get(list_url)
        resp.raise_for_status()

        def _parse_listing(xml_text: str) -> list[ModificationFileInfo]:
            result = []
            for block in re.finditer(r"<Contents>(.*?)</Contents>", xml_text, re.DOTALL):
                content = block.group(1)
                km = re.search(r"<Key>(.*?)</Key>", content)
                sm = re.search(r"<Size>(\d+)</Size>", content)
                em = re.search(r"<ETag>(.*?)</ETag>", content)
                if not (km and sm and em):
                    continue
                key_name = km.group(1)
                size = int(sm.group(1))
                raw_etag = em.group(1)
                rel_path = key_name.replace(folder + "/", "", 1) if folder else key_name
                if not rel_path:
                    continue
                etag = raw_etag.replace('"', "").replace("&#34;", "").strip()
                result.append(ModificationFileInfo(
                    file_name=rel_path,
                    hash=etag,
                    size=size,
                ))
            return result

        files = _parse_listing(resp.text)

        if not files:
            listing_url = f"{base}/{bucket}/{folder}/"
            resp2 = await self._client.get(listing_url)
            resp2.raise_for_status()
            files = _parse_listing(resp2.text)

        return files

    async def download_s3_file(self, filename: str, mod: Mod) -> bytes:
        md = mod.mod_data
        if not md:
            raise ValueError("No mod data")
        host = md.s3_host_link or ""
        bucket = md.s3_bucket_name or ""
        folder = md.s3_folder_name or ""
        base = self._base_url(host)
        url = f"{base}/{bucket}/{folder}/{filename}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.content

    async def close(self):
        await self._client.aclose()
