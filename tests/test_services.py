import os
import tempfile

import pytest

import hashlib
import json
import os
import tempfile
import zipfile
from unittest.mock import patch

import pytest

from genlauncher_tui.config import CONFIG
from genlauncher_tui.models.enums import InstallMethod
from genlauncher_tui.models.mod import Mod, ModData
from genlauncher_tui.models.options import LauncherOptions
from genlauncher_tui.models.repo import ModAddonsAndPatches, ReposModsData
from genlauncher_tui.services.download_manager import (
    extract_archive,
    get_all_files_recursively,
    get_md5,
    get_total_size,
)
from genlauncher_tui.services.mod_service import ModService, MODLIST_FILE, _mime_to_ext
from genlauncher_tui.services.options_service import OptionsService
from genlauncher_tui.services.repo_service import RepoService
from genlauncher_tui.services.symlink_service import SymLinkService
from genlauncher_tui.services.steam_service import SteamService


class TestConfig:
    def test_repo_urls_exist(self):
        assert "repos" in CONFIG
        assert "ZH" in CONFIG["repos"]
        assert CONFIG["repos"]["ZH"].startswith("http")

    def test_extra_urls_exist(self):
        assert "extra" in CONFIG
        assert "modded_exe_download_link" in CONFIG["extra"]
        assert "gentool_download_link" in CONFIG["extra"]
        assert "gentool_dll_hash" in CONFIG["extra"]


class TestSymLinkService:
    def test_is_symlinks_supported_returns_bool(self):
        result = SymLinkService.is_symlinks_supported()
        assert isinstance(result, bool)
        # On Linux this should be True
        import platform
        if platform.system() == "Linux":
            assert result is True, "Symlinks should be supported on Linux"

    def test_create_symlink_roundtrip(self):
        if not SymLinkService.is_symlinks_supported():
            pytest.skip("Symlinks not supported on this platform")
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "source.txt")
            link = os.path.join(tmpdir, "link.txt")
            with open(src, "w") as f:
                f.write("hello")
            result = SymLinkService.create_symlink(link, src)
            assert result is True
            assert os.path.islink(link)
            with open(link) as f:
                assert f.read() == "hello"


class TestRepoServce:
    @pytest.mark.asyncio
    async def test_fetch_repo_data_returns_mods(self):
        svc = RepoService()
        data = await svc.fetch_repo_data()
        assert data is not None
        assert len(data.mod_datas) > 0, "Expected at least one mod in the repo"

    @pytest.mark.asyncio
    async def test_fetch_repo_data_has_mod_names(self):
        svc = RepoService()
        data = await svc.fetch_repo_data()
        names = [m.mod_name for m in data.mod_datas]
        assert all(n for n in names), "All mods should have non-empty names"

    @pytest.mark.asyncio
    async def test_fetch_repo_data_is_cached(self):
        svc = RepoService()
        data1 = await svc.fetch_repo_data()
        data2 = await svc.fetch_repo_data()
        assert data1 is data2, "Second call should return cached data"

    @pytest.mark.asyncio
    async def test_repo_url_is_zh(self):
        svc = RepoService()
        url = svc.get_repo_url()
        assert "ReposModificationDataZH3" in url


class TestModService:
    def _make_repo_data(self, *names: str) -> ReposModsData:
        data = ReposModsData()
        for name in names:
            data.mod_datas.append(ModAddonsAndPatches(mod_name=name))
        return data

    def _patch_mod_dir(self, tmpdir: str):
        """Patch SteamService.get_mod_dir to return a temp dir."""
        return patch.object(SteamService, "get_mod_dir", return_value=tmpdir)

    def test_add_mod_to_list(self):
        data = self._make_repo_data("Test Mod A", "Test Mod B")
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_mod_dir(tmpdir):
                svc = ModService(repo_data=data)
                assert len(svc.get_added_mods()) == 0

                result = svc.add_mod_to_list("Test Mod A")
                assert result is True
                added = svc.get_added_mods()
                assert len(added) == 1
                assert added[0].mod_info.mod_name == "Test Mod A"

    def test_add_mod_to_list_duplicate(self):
        data = self._make_repo_data("Test Mod A")
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_mod_dir(tmpdir):
                svc = ModService(repo_data=data)
                svc.add_mod_to_list("Test Mod A")
                result = svc.add_mod_to_list("Test Mod A")
                assert result is False
                assert len(svc.get_added_mods()) == 1

    def test_add_mod_to_list_not_found(self):
        data = self._make_repo_data("Test Mod A")
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_mod_dir(tmpdir):
                svc = ModService(repo_data=data)
                result = svc.add_mod_to_list("Nonexistent Mod")
                assert result is False
                assert len(svc.get_added_mods()) == 0

    def test_add_mod_to_list_no_repo_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_mod_dir(tmpdir):
                svc = ModService()
                assert svc._repo_data is None
                result = svc.add_mod_to_list("Test Mod")
                assert result is False

    def test_remove_mod_from_list(self):
        data = self._make_repo_data("Test Mod A")
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_mod_dir(tmpdir):
                svc = ModService(repo_data=data)
                svc.add_mod_to_list("Test Mod A")
                assert len(svc.get_added_mods()) == 1

                result = svc.remove_mod_from_list("Test Mod A")
                assert result is True
                assert len(svc.get_added_mods()) == 0

    def test_remove_mod_not_found(self):
        data = self._make_repo_data("Test Mod A")
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_mod_dir(tmpdir):
                svc = ModService(repo_data=data)
                result = svc.remove_mod_from_list("Nonexistent")
                assert result is False

    def test_get_unadded_mods(self):
        data = self._make_repo_data("Mod A", "Mod B", "Mod C")
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_mod_dir(tmpdir):
                svc = ModService(repo_data=data)
                svc.add_mod_to_list("Mod A")

                unadded = svc.get_unadded_mods()
                names = [m.mod_name for m in unadded.mod_datas]
                assert "Mod A" not in names
                assert "Mod B" in names
                assert "Mod C" in names
                assert len(names) == 2

    def test_get_unadded_mods_no_repo_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_mod_dir(tmpdir):
                svc = ModService()
                unadded = svc.get_unadded_mods()
                assert len(unadded.mod_datas) == 0

    def test_persistence_roundtrip(self):
        data = self._make_repo_data("Mod Persist A", "Mod Persist B")
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_mod_dir(tmpdir):
                # First instance
                svc1 = ModService(repo_data=data)
                svc1.add_mod_to_list("Mod Persist A")
                svc1.add_mod_to_list("Mod Persist B")
                assert len(svc1.get_added_mods()) == 2

            with self._patch_mod_dir(tmpdir):
                # Second instance should read the persisted JSON
                svc2 = ModService(repo_data=data)
                added = svc2.get_added_mods()
                assert len(added) == 2
                names = [m.mod_info.mod_name for m in added]
                assert "Mod Persist A" in names
                assert "Mod Persist B" in names

    def test_remove_after_persistence(self):
        data = self._make_repo_data("Mod A", "Mod B")
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_mod_dir(tmpdir):
                svc = ModService(repo_data=data)
                svc.add_mod_to_list("Mod A")
                svc.add_mod_to_list("Mod B")

            with self._patch_mod_dir(tmpdir):
                svc2 = ModService(repo_data=data)
                svc2.remove_mod_from_list("Mod A")
                assert len(svc2.get_added_mods()) == 1
                assert svc2.get_added_mods()[0].mod_info.mod_name == "Mod B"

            with self._patch_mod_dir(tmpdir):
                svc3 = ModService(repo_data=data)
                assert len(svc3.get_added_mods()) == 1
                assert svc3.get_added_mods()[0].mod_info.mod_name == "Mod B"


class TestOptionsService:
    def _patch_app_data_dir(self, tmpdir: str):
        return patch.object(OptionsService, "get_app_data_folder", return_value=tmpdir)

    def test_default_options_are_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_app_data_dir(tmpdir):
                svc = OptionsService()
                opts = svc.get_options()
                assert opts.install_method in (InstallMethod.SymLink, InstallMethod.CopyFiles)
                assert isinstance(opts.steam_path, str)

    def test_set_options_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_app_data_dir(tmpdir):
                svc = OptionsService()
                new_opts = LauncherOptions(
                    install_method=InstallMethod.CopyFiles,
                    steam_path="/custom/steam/path",
                )
                saved = svc.set_options(new_opts)
                assert saved.install_method == InstallMethod.CopyFiles
                assert saved.steam_path == "/custom/steam/path"

                # New instance should read the saved values
                svc2 = OptionsService()
                loaded = svc2.get_options()
                assert loaded.install_method == InstallMethod.CopyFiles
                assert loaded.steam_path == "/custom/steam/path"

    def test_reset_options(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_app_data_dir(tmpdir):
                svc = OptionsService()
                svc.set_options(LauncherOptions(
                    install_method=InstallMethod.CopyFiles,
                    steam_path="/custom/steam/path",
                ))
                reset = svc.reset_options()
                # On Linux, default is SymLink
                assert reset.install_method == InstallMethod.SymLink
                # steam_path gets auto-filled by _fix_options(), may or may not be empty
                assert isinstance(reset.steam_path, str)

    def test_options_file_is_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self._patch_app_data_dir(tmpdir):
                from genlauncher_tui.services.options_service import OPTIONS_FILENAME
                opts_path = os.path.join(tmpdir, OPTIONS_FILENAME)
                assert not os.path.isfile(opts_path)

                svc = OptionsService()
                svc.set_options(LauncherOptions(
                    install_method=InstallMethod.CopyFiles,
                    steam_path="/test/path",
                ))
                assert os.path.isfile(opts_path)
                with open(opts_path) as f:
                    data = json.load(f)
                assert data["install_method"] == "CopyFiles"
                assert data["steam_path"] == "/test/path"


class TestDownloadManager:
    def test_get_md5(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.bin")
            data = b"hello world"
            with open(path, "wb") as f:
                f.write(data)
            expected = hashlib.md5(data).hexdigest()
            assert get_md5(path) == expected

    def test_get_md5_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "empty.bin")
            with open(path, "wb") as f:
                pass
            expected = hashlib.md5(b"").hexdigest()
            assert get_md5(path) == expected

    def test_get_all_files_recursively(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "subdir"))
            open(os.path.join(tmpdir, "file1.txt"), "w").close()
            open(os.path.join(tmpdir, "subdir", "file2.txt"), "w").close()

            files = get_all_files_recursively(tmpdir)
            assert len(files) == 2
            assert any(f.endswith("file1.txt") for f in files)
            assert any(f.endswith("file2.txt") for f in files)

    def test_get_all_files_recursively_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = get_all_files_recursively(tmpdir)
            assert files == []

    def test_get_total_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p1 = os.path.join(tmpdir, "a.bin")
            p2 = os.path.join(tmpdir, "b.bin")
            with open(p1, "wb") as f:
                f.write(b"x" * 100)
            with open(p2, "wb") as f:
                f.write(b"y" * 200)
            total = get_total_size([p1, p2])
            assert total == 300

    def test_get_total_size_empty_list(self):
        assert get_total_size([]) == 0

    def test_extract_zip_archive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "test.zip")
            extract_dir = os.path.join(tmpdir, "extracted")
            inner_dir = os.path.join(tmpdir, "inner")
            os.makedirs(inner_dir)
            inner_file = os.path.join(inner_dir, "mod.big")
            with open(inner_file, "wb") as f:
                f.write(b"mod data")

            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.write(inner_file, arcname="mods/mod.big")

            extracted = extract_archive(zip_path, extract_dir)
            assert len(extracted) >= 1
            extracted_path = os.path.join(extract_dir, "mods", "mod.big")
            assert os.path.isfile(extracted_path)
            with open(extracted_path) as f:
                assert f.read() == "mod data"

            # archive should be deleted after extraction
            assert not os.path.isfile(zip_path)


class TestDownloadManagerExtraction:
    def test_extract_7z_missing_dependency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dummy = os.path.join(tmpdir, "mod.7z")
            with open(dummy, "wb") as f:
                f.write(b"fake 7z content")
            dest = os.path.join(tmpdir, "out")
            with pytest.raises(RuntimeError, match="py7zr"):
                extract_archive(dummy, dest)

    def test_extract_rar_missing_dependency(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dummy = os.path.join(tmpdir, "mod.rar")
            with open(dummy, "wb") as f:
                f.write(b"fake rar content")
            dest = os.path.join(tmpdir, "out")
            with pytest.raises(RuntimeError, match="rarfile"):
                extract_archive(dummy, dest)

    def test_mime_to_ext_variants(self):
        assert _mime_to_ext("application/zip") == ".zip"
        assert _mime_to_ext("application/x-7z-compressed") == ".7z"
        assert _mime_to_ext("application/x-rar-compressed") == ".rar"
        assert _mime_to_ext("application/gzip") == ".gz"
        assert _mime_to_ext("application/x-tar") == ".tar"
        assert _mime_to_ext("unknown/thing") == ".zip"
        assert _mime_to_ext("something/zip") == ".zip"
        assert _mime_to_ext("something/7-zip") == ".7z"
        assert _mime_to_ext("something/rar") == ".rar"


class TestModServiceInstall:
    def _make_repo_data(self, *names: str) -> ReposModsData:
        data = ReposModsData()
        for name in names:
            data.mod_datas.append(ModAddonsAndPatches(mod_name=name))
        return data

    def test_install_mod_unknown_mod(self):
        data = self._make_repo_data("Mod A")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(SteamService, "get_mod_dir", return_value=tmpdir):
                with patch.object(SteamService, "get_game_install_dir", return_value=tmpdir):
                    svc = ModService(repo_data=data)
                    with pytest.raises(ValueError, match="Mod not found"):
                        svc.install_mod("Nonexistent", InstallMethod.CopyFiles)

    def test_install_mod_another_mod_installed(self):
        data = self._make_repo_data("Mod A", "Mod B")
        with tempfile.TemporaryDirectory() as tmpdir:
            mods_dir = os.path.join(tmpdir, "mods")
            game_dir = os.path.join(tmpdir, "game")
            os.makedirs(mods_dir)
            os.makedirs(game_dir)
            generals_exe = os.path.join(game_dir, "Generals.exe")
            with open(generals_exe, "w") as f:
                f.write("exe")
            modded_dir = os.path.join(mods_dir, "ModdedLauncher")
            os.makedirs(modded_dir)
            modded_exe = os.path.join(modded_dir, "modded.exe")
            with open(modded_exe, "w") as f:
                f.write("exe")

            with patch.object(SteamService, "get_mod_dir", return_value=mods_dir):
                with patch.object(SteamService, "get_game_install_dir", return_value=game_dir):
                    svc = ModService(repo_data=data)
                    svc.add_mod_to_list("Mod A")
                    svc.add_mod_to_list("Mod B")
                    ma = svc.get_added_mods()[0]
                    ma.downloaded = True
                    ma.downloaded_files = ["a.big"]
                    ma.mod_dir = mods_dir
                    a_path = os.path.join(mods_dir, "a.big")
                    with open(a_path, "w") as f:
                        f.write("mod a")
                    mb = svc.get_added_mods()[1]
                    mb.downloaded = True
                    mb.downloaded_files = ["b.big"]
                    mb.mod_dir = mods_dir

                    svc.install_mod("Mod A", InstallMethod.CopyFiles)
                    with pytest.raises(RuntimeError, match="already installed"):
                        svc.install_mod("Mod B", InstallMethod.CopyFiles)

    def test_install_mod_mod_folder_missing(self):
        data = self._make_repo_data("Mod A")
        with tempfile.TemporaryDirectory() as tmpdir:
            mods_dir = os.path.join(tmpdir, "mods")
            game_dir = os.path.join(tmpdir, "game")
            os.makedirs(mods_dir)
            os.makedirs(game_dir)
            generals_exe = os.path.join(game_dir, "Generals.exe")
            with open(generals_exe, "w") as f:
                f.write("exe")
            modded_dir = os.path.join(mods_dir, "ModdedLauncher")
            os.makedirs(modded_dir)
            modded_exe = os.path.join(modded_dir, "modded.exe")
            with open(modded_exe, "w") as f:
                f.write("exe")

            with patch.object(SteamService, "get_mod_dir", return_value=mods_dir):
                with patch.object(SteamService, "get_game_install_dir", return_value=game_dir):
                    svc = ModService(repo_data=data)
                    svc.add_mod_to_list("Mod A")
                    mod = svc.get_added_mods()[0]
                    mod.downloaded = True
                    mod.downloaded_files = ["a.big"]
                    mod.mod_dir = "/nonexistent/path"
                    with pytest.raises(FileNotFoundError, match="Mod folder"):
                        svc.install_mod("Mod A", InstallMethod.CopyFiles)

    def test_install_mod_copy_files(self):
        data = self._make_repo_data("Test Mod")
        with tempfile.TemporaryDirectory() as tmpdir:
            mods_dir = os.path.join(tmpdir, "mods")
            game_dir = os.path.join(tmpdir, "game")
            os.makedirs(mods_dir)
            os.makedirs(game_dir)
            generals_exe = os.path.join(game_dir, "Generals.exe")
            with open(generals_exe, "w") as f:
                f.write("exe")
            modded_dir = os.path.join(mods_dir, "ModdedLauncher")
            os.makedirs(modded_dir)
            modded_exe = os.path.join(modded_dir, "modded.exe")
            with open(modded_exe, "w") as f:
                f.write("exe")

            mod_folder = os.path.join(mods_dir, "test_mod")
            os.makedirs(mod_folder)
            mod_file = os.path.join(mod_folder, "mod.big")
            with open(mod_file, "w") as f:
                f.write("mod data")

            with patch.object(SteamService, "get_mod_dir", return_value=mods_dir):
                with patch.object(SteamService, "get_game_install_dir", return_value=game_dir):
                    svc = ModService(repo_data=data)
                    svc.add_mod_to_list("Test Mod")
                    mod = svc.get_added_mods()[0]
                    mod.downloaded = True
                    mod.downloaded_files = ["mod.big"]
                    mod.mod_dir = mod_folder

                    svc.install_mod("Test Mod", InstallMethod.CopyFiles)

                    dest = os.path.join(game_dir, "mod.big")
                    assert os.path.isfile(dest)
                    with open(dest) as f:
                        assert f.read() == "mod data"
                    assert mod.installed is True

    def test_install_mod_symlink(self):
        if not SymLinkService.is_symlinks_supported():
            pytest.skip("Symlinks not supported")
        data = self._make_repo_data("Test Mod")
        with tempfile.TemporaryDirectory() as tmpdir:
            mods_dir = os.path.join(tmpdir, "mods")
            game_dir = os.path.join(tmpdir, "game")
            os.makedirs(mods_dir)
            os.makedirs(game_dir)
            generals_exe = os.path.join(game_dir, "Generals.exe")
            with open(generals_exe, "w") as f:
                f.write("exe")
            modded_dir = os.path.join(mods_dir, "ModdedLauncher")
            os.makedirs(modded_dir)
            modded_exe = os.path.join(modded_dir, "modded.exe")
            with open(modded_exe, "w") as f:
                f.write("exe")

            mod_folder = os.path.join(mods_dir, "test_mod")
            os.makedirs(mod_folder)
            mod_file = os.path.join(mod_folder, "mod.big")
            with open(mod_file, "w") as f:
                f.write("mod data")

            with patch.object(SteamService, "get_mod_dir", return_value=mods_dir):
                with patch.object(SteamService, "get_game_install_dir", return_value=game_dir):
                    svc = ModService(repo_data=data)
                    svc.add_mod_to_list("Test Mod")
                    mod = svc.get_added_mods()[0]
                    mod.downloaded = True
                    mod.downloaded_files = ["mod.big"]
                    mod.mod_dir = mod_folder

                    svc.install_mod("Test Mod", InstallMethod.SymLink)

                    dest = os.path.join(game_dir, "mod.big")
                    assert os.path.islink(dest)
                    assert os.path.realpath(dest) == os.path.realpath(mod_file)
                    assert mod.installed is True

    def test_uninstall_mod_unknown_mod(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(SteamService, "get_mod_dir", return_value=tmpdir):
                with patch.object(SteamService, "get_game_install_dir", return_value=tmpdir):
                    svc = ModService()
                    svc.uninstall_mod("Nonexistent")

    def test_uninstall_mod_removes_files(self):
        data = self._make_repo_data("Test Mod")
        with tempfile.TemporaryDirectory() as tmpdir:
            mods_dir = os.path.join(tmpdir, "mods")
            game_dir = os.path.join(tmpdir, "game")
            os.makedirs(mods_dir)
            os.makedirs(game_dir)
            generals_exe = os.path.join(game_dir, "Generals.exe")
            with open(generals_exe, "w") as f:
                f.write("exe")
            modded_dir = os.path.join(mods_dir, "ModdedLauncher")
            os.makedirs(modded_dir)
            modded_exe = os.path.join(modded_dir, "modded.exe")
            with open(modded_exe, "w") as f:
                f.write("exe")

            mod_folder = os.path.join(mods_dir, "test_mod")
            os.makedirs(mod_folder)
            mod_file = os.path.join(mod_folder, "mod.big")
            with open(mod_file, "w") as f:
                f.write("mod data")

            with patch.object(SteamService, "get_mod_dir", return_value=mods_dir):
                with patch.object(SteamService, "get_game_install_dir", return_value=game_dir):
                    svc = ModService(repo_data=data)
                    svc.add_mod_to_list("Test Mod")
                    mod = svc.get_added_mods()[0]
                    mod.downloaded = True
                    mod.downloaded_files = ["mod.big"]
                    mod.mod_dir = mod_folder
                    svc.install_mod("Test Mod", InstallMethod.CopyFiles)

                    dest = os.path.join(game_dir, "mod.big")
                    assert os.path.isfile(dest)

                    svc.uninstall_mod("Test Mod")

                    assert not os.path.isfile(dest)
                    assert mod.installed is False


class TestModServiceDelete:
    def _make_repo_data(self, *names: str) -> ReposModsData:
        data = ReposModsData()
        for name in names:
            data.mod_datas.append(ModAddonsAndPatches(mod_name=name))
        return data

    def test_delete_mod_removes_directory(self):
        data = self._make_repo_data("Test Mod")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(SteamService, "get_mod_dir", return_value=tmpdir):
                svc = ModService(repo_data=data)
                svc.add_mod_to_list("Test Mod")
                mod = svc.get_added_mods()[0]
                mod_folder = os.path.join(tmpdir, "test_mod")
                os.makedirs(mod_folder)
                mod_file = os.path.join(mod_folder, "data.big")
                with open(mod_file, "w") as f:
                    f.write("data")
                mod.mod_dir = mod_folder
                mod.downloaded = True

                assert os.path.isdir(mod_folder)
                svc.delete_mod("Test Mod")
                assert not os.path.isdir(mod_folder)

    def test_delete_mod_resets_state(self):
        data = self._make_repo_data("Test Mod")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(SteamService, "get_mod_dir", return_value=tmpdir):
                svc = ModService(repo_data=data)
                svc.add_mod_to_list("Test Mod")
                mod = svc.get_added_mods()[0]
                mod.downloaded = True
                mod.downloaded_version = "1.0"
                mod.downloaded_files = ["a.big"]
                mod.total_size = 100
                mod.mod_dir = "/tmp/foo"

                svc.delete_mod("Test Mod")
                assert mod.downloaded is False
                assert mod.downloaded_version == ""
                assert mod.installed is False
                assert mod.downloaded_files is None
                assert mod.total_size == 0
                assert mod.mod_dir is None

    def test_delete_mod_unknown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(SteamService, "get_mod_dir", return_value=tmpdir):
                svc = ModService()
                svc.delete_mod("Nonexistent")


class TestModServiceDirectoryCreation:
    def test_modlist_path_creates_directory(self):
        data = ReposModsData()
        data.mod_datas.append(ModAddonsAndPatches(mod_name="Mod A"))
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "a", "b", "c")
            with patch.object(SteamService, "get_mod_dir", return_value=nested):
                svc = ModService(repo_data=data)
                svc.add_mod_to_list("Mod A")
                modlist = os.path.join(nested, MODLIST_FILE)
                assert os.path.isfile(modlist), "Modlist file should exist"
                assert os.path.isdir(nested), "Directory should have been created"
