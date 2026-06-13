from __future__ import annotations

import hashlib
import os
import zipfile
from pathlib import Path
from typing import Callable, Optional

import httpx

_PROGRESS_CALLBACK = Optional[Callable[[int, int], None]]


async def download_file(
    url: str,
    dest_path: str,
    progress_callback: _PROGRESS_CALLBACK = None,
) -> str:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(dest_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(downloaded, total)
    return dest_path


async def download_bytes(
    url: str,
    progress_callback: _PROGRESS_CALLBACK = None,
) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            ct = resp.headers.get("content-type", "")
            chunks = []
            downloaded = 0
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                chunks.append(chunk)
                downloaded += len(chunk)
                if progress_callback and total:
                    progress_callback(downloaded, total)
            return b"".join(chunks), ct


def extract_archive(file_path: str, dest_dir: str) -> list[str]:
    os.makedirs(dest_dir, exist_ok=True)
    extracted = []
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".zip":
        with zipfile.ZipFile(file_path) as zf:
            zf.extractall(dest_dir)
        for root, dirs, files in os.walk(dest_dir):
            for f in files:
                extracted.append(os.path.join(root, f))

    elif ext == ".7z":
        try:
            import py7zr
            with py7zr.SevenZipFile(file_path, mode="r") as sz:
                sz.extractall(path=dest_dir)
            for root, dirs, files in os.walk(dest_dir):
                for f in files:
                    extracted.append(os.path.join(root, f))
        except ImportError:
            raise RuntimeError("py7zr is required to extract .7z files: pip install py7zr")

    elif ext == ".rar":
        try:
            import rarfile
            with rarfile.RarFile(file_path) as rf:
                rf.extractall(dest_dir)
            for root, dirs, files in os.walk(dest_dir):
                for f in files:
                    extracted.append(os.path.join(root, f))
        except ImportError:
            raise RuntimeError("rarfile is required to extract .rar files: pip install rarfile")

    os.unlink(file_path)
    return extracted


def get_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_all_files_recursively(path: str) -> list[str]:
    files = []
    try:
        for root, dirs, filenames in os.walk(path):
            for f in filenames:
                files.append(os.path.join(root, f))
    except (PermissionError, OSError):
        pass
    return files


def get_total_size(file_paths: list[str]) -> int:
    total = 0
    for fp in file_paths:
        try:
            total += os.path.getsize(fp)
        except OSError:
            pass
    return total
