from __future__ import annotations

import dataclasses
import hashlib
import hmac
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qsl, quote, urlencode, urlparse

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

    @staticmethod
    def _aws_v4_signed_headers(
        method: str,
        url: str,
        headers: dict[str, str] | None,
        body: bytes,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        service: str = "s3",
    ) -> dict[str, str]:
        parsed = urlparse(url)
        canonical_uri = parsed.path or "/"
        params = parse_qsl(parsed.query, keep_blank_values=True)
        canonical_qs = urlencode(sorted(params), quote_via=lambda s, safe, encoding, errors: quote(s, safe="~"))
        payload_hash = hashlib.sha256(body).hexdigest()
        amz_date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        date_stamp = amz_date[:8]

        if headers is None:
            headers = {}
        host_header = parsed.hostname or ""
        if parsed.port:
            host_header = f"{host_header}:{parsed.port}"
        headers["host"] = host_header
        headers["x-amz-date"] = amz_date
        headers["x-amz-content-sha256"] = payload_hash

        canonical_headers = "".join(f"{k.lower()}:{v.strip()}\n" for k, v in sorted(headers.items()))
        signed_headers = ";".join(sorted(headers))
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_qs}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = (
            f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        )

        k_date = hmac.new(f"AWS4{secret_key}".encode(), date_stamp.encode(), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region.encode(), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service.encode(), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, "aws4_request".encode(), hashlib.sha256).digest()
        signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

        headers["Authorization"] = (
            f"AWS4-HMAC-SHA256 "
            f"Credential={access_key}/{credential_scope},"
            f"SignedHeaders={signed_headers},"
            f"Signature={signature}"
        )
        return headers

    async def _signed_get(self, url: str, access_key: str, secret_key: str) -> httpx.Response:
        headers = self._aws_v4_signed_headers("GET", url, None, b"", access_key, secret_key)
        return await self._client.get(url, headers=headers)

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
        resp = await self._signed_get(list_url, key, secret)
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
            resp2 = await self._signed_get(listing_url, key, secret)
            resp2.raise_for_status()
            files = _parse_listing(resp2.text)

        return files

    async def download_s3_file(self, filename: str, mod: Mod) -> bytes:
        md = mod.mod_data
        if not md:
            raise ValueError("No mod data")
        key = (md.s3_host_public_key or GEN_INS_A_PKEY).strip()
        secret = (md.s3_host_secret_key or GEN_INS_A_SKEY).strip()
        host = md.s3_host_link or ""
        bucket = md.s3_bucket_name or ""
        folder = md.s3_folder_name or ""
        base = self._base_url(host)
        url = f"{base}/{bucket}/{folder}/{filename}"
        resp = await self._signed_get(url, key, secret)
        resp.raise_for_status()
        return resp.content

    async def close(self):
        await self._client.aclose()
