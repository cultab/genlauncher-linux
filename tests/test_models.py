from genlauncher_tui.models.enums import ModificationType, InstallMethod, GameType
from genlauncher_tui.models.mod import Mod, ModData, clean_string, standard_mod_name, fix_mod_filename
from genlauncher_tui.models.repo import ReposModsData, ModAddonsAndPatches
from genlauncher_tui.models.options import LauncherOptions, InstallationStatus


class TestEnums:
    def test_modification_type_values(self):
        assert ModificationType.Mod.value == "Mod"
        assert ModificationType.Addon.value == "Addon"
        assert ModificationType.Patch.value == "Patch"
        assert ModificationType.Advertising.value == "Advertising"

    def test_install_method_values(self):
        assert InstallMethod.CopyFiles.value == "CopyFiles"
        assert InstallMethod.SymLink.value == "SymLink"

    def test_game_type_values(self):
        assert GameType.Gen.value == 1
        assert GameType.ZH.value == 2


class TestStringUtils:
    def test_clean_string_removes_non_ascii(self):
        assert clean_string("Rise of the Reds") == "Rise_of_the_Reds"

    def test_clean_string_removes_special_chars(self):
        # Only letters survive; digits, punctuation and symbols are stripped
        assert clean_string("Mod v2.0!") == "Mod_v"

    def test_standard_mod_name(self):
        assert standard_mod_name("Hello World!") == "helloworld"
        assert standard_mod_name("C&C Generals") == "ccgenerals"

    def test_fix_mod_filename_gib_to_big(self):
        assert fix_mod_filename("test.gib") == "test.big"

    def test_fix_mod_filename_unchanged(self):
        assert fix_mod_filename("test.big") == "test.big"
        assert fix_mod_filename("data.zip") == "data.zip"


class TestModData:
    def test_default_values(self):
        md = ModData()
        assert md.name == ""
        assert md.version == ""
        assert md.is_selected is False
        assert md.installed is False
        assert md.modification_type == ModificationType.Mod

    def test_equality_by_name_and_version(self):
        a = ModData(name="Test Mod", version="1.0")
        b = ModData(name="test mod", version="1.0")
        assert a == b

    def test_inequality_different_version(self):
        a = ModData(name="Test Mod", version="1.0")
        b = ModData(name="Test Mod", version="2.0")
        assert a != b

    def test_comparison(self):
        a = ModData(name="Mod A", version="1.0")
        b = ModData(name="Mod B", version="2.0")
        assert a.compare_to(b) < 0
        assert b.compare_to(a) > 0
        assert a.compare_to(a) == 0

    def test_union_merges_fields(self):
        base = ModData(name="Test", simple_download_link=None)
        other = ModData(name="Test", simple_download_link="https://example.com/mod")
        base.union(other)
        assert base.simple_download_link == "https://example.com/mod"


class TestMod:
    def test_cleaned_mod_name_with_info(self):
        from genlauncher_tui.models.repo import ModAddonsAndPatches
        m = Mod(mod_info=ModAddonsAndPatches(mod_name="Rise of the Reds"))
        assert m.cleaned_mod_name == "Rise_of_the_Reds"

    def test_cleaned_mod_name_no_info(self):
        m = Mod()
        assert m.cleaned_mod_name == ""

    def test_has_s3_storage(self):
        m = Mod(mod_data=ModData(s3_host_link="s3.example.com", s3_folder_name="mods", s3_bucket_name="bucket"))
        assert m.has_s3_storage() is True

    def test_no_s3_storage(self):
        m = Mod(mod_data=ModData())
        assert m.has_s3_storage() is False

    def test_no_s3_storage_no_mod_data(self):
        m = Mod()
        assert m.has_s3_storage() is False


class TestReposModsData:
    def test_default_lists_are_empty(self):
        data = ReposModsData()
        assert data.mod_datas == []
        assert data.global_addons_data == []
        assert data.original_game_addons == []
        assert data.original_game_patches == []
        assert data.adv_data == []

    def test_mod_addons_and_patches_defaults(self):
        m = ModAddonsAndPatches()
        assert m.mod_patches == []
        assert m.mod_addons == []


class TestOptions:
    def test_launcher_options_defaults(self):
        opts = LauncherOptions()
        assert opts.install_method == InstallMethod.CopyFiles
        assert opts.steam_path == ""

    def test_installation_status_defaults(self):
        status = InstallationStatus()
        assert status.modded_launcher is False
        assert status.gen_tool is False
