from genlauncher_tui.models.mod import Mod, ModData, clean_string, standard_mod_name, fix_mod_filename


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

    def test_has_s3_storage(self):
        m = Mod(mod_data=ModData(s3_host_link="s3.example.com", s3_folder_name="mods", s3_bucket_name="bucket"))
        assert m.has_s3_storage() is True

    def test_no_s3_storage(self):
        m = Mod(mod_data=ModData())
        assert m.has_s3_storage() is False
