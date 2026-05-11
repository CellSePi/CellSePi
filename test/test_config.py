import ast

import pytest

from backend.main_window.constants import FileType
from src.cellsepi.backend.main_window.config_file import ConfigFile

from src.cellsepi.backend.main_window.config_file import create_default_config, DeletionForbidden


@pytest.fixture
def config():
    cfg = ConfigFile()
    cfg.clear_config()
    yield cfg
    cfg.restore_config()

def test_add_and_delete_profile(config):
    config.add_profile("test", "42", "n", "j", 2.0)
    default_config = create_default_config()
    assert config.config != default_config, "The config did not change"
    assert "test" in config.config["Profiles"], "The new profile was not added"
    assert "42" == config.config["Profiles"]["test"]["bf_channel"], "The bf_channel is not right"
    assert "n" == config.config["Profiles"]["test"]["mask_suffix"], "The mask_suffix is not right"
    assert "j" == config.config["Profiles"]["test"]["channel_prefix"], "The channel_prefix is not right"
    assert 2.0 == config.config["Profiles"]["test"]["diameter"], "The diameter is not right"
    config.delete_profile("test")
    assert config.config == default_config, "test is not deleted"

def test_if_config_is_empty(config):
    assert config.config == create_default_config(),"empty file did not construct right"

def test_if_config_is_not_existing(config):
    assert config.config == create_default_config(),"new file did not construct right"

def test_get_profile(config):
    assert config.get_profile("Lif") == create_default_config()["Profiles"]["Lif"], "Something get wrong by getting profile"

def test_update_profile(config):
    config.update_profile("Lif", "42")
    assert config.get_profile("Lif")["bf_channel"] == "42", "Values not changed after update"

def test_add_profile_name_fail(config):
    assert False == config.add_profile("Lif", 42, "n", "j", 2.0), "Adding should fail"

def test_rename_profile_name(config):
    assert True == config.rename_profile("Lif", "Lif2"), "Something went wrong with renaming"
    assert "Lif2" in config.config["Profiles"], "The profile name was not renamed"
    assert True == config.rename_profile("Lif2", "Lif2"), "Renaming should just return True because old and new are equal"
    assert False == config.rename_profile("Lif3","Lif2"), "Renaming should fail, because Lif3 not exists"
    assert False == config.rename_profile("Lif3", "Tif"), "Renaming should fail, because Tif is already taken"

def test_selected_profile_name(config):
    config.select_profile("Tif")
    assert config.get_selected_profile_name() == "Tif", "Selected profile was not changed"
    assert config.get_selected_profile() == create_default_config()["Profiles"]["Tif"], "Selected profile is wrong"

def test_delete_selected_profile_name(config):
    config.select_profile("Tif")
    config.delete_profile("Tif")
    assert config.get_selected_profile_name() == "Lif", "Selected profile was not changed after deleted"

def test_set_colors(config):
    config.set_mask_color((12,42,69))
    assert config.get_mask_color() == (12,42,69), "The mask_color is not right"
    config.set_outline_color((21,24,96))
    assert config.get_outline_color() == (21,24,96), "The outline_color is not right"

def test_states(config):
    config.set_auto_button(True)
    assert config.get_auto_button() == True, "The auto_button is not right"
    config.set_auto_button(False)
    assert config.get_auto_button() == False, "The auto_button is not right"
    for file_type in FileType:
        config.set_file_type_slider(file_type)
        assert config.get_file_type_slider() == file_type, "The auto_button is not right"

def test_attribute_getter(config):
    assert config.get_bf_channel() == create_default_config()["Profiles"]["Lif"]["bf_channel"], "bf_channel is wrong"
    assert config.get_mask_suffix() == create_default_config()["Profiles"]["Lif"]["mask_suffix"], "mask_suffix is wrong"
    assert config.get_channel_prefix() == create_default_config()["Profiles"]["Lif"]["channel_prefix"],"channel_prefix is wrong"
    assert config.get_diameter() == float(create_default_config()["Profiles"]["Lif"]["diameter"]),"diameter is wrong"
    assert config.get_mask_color() ==  ast.literal_eval(create_default_config()["Colors"]["mask"]),"mask_color is wrong"
    assert config.get_outline_color() ==  ast.literal_eval(create_default_config()["Colors"]["outline"]),"outline_color is wrong"

def test_idx_name(config):
    assert config.name_to_index("Lif") == 0, "Idx is wrong for Lif"
    assert config.index_to_name(0) == "Lif", "Lif is wrong for this IDX"

def test_invalid_profile(config):
        with pytest.raises(ValueError):
            config.add_profile("", "42", "", "", -10)
        with pytest.raises(ValueError):
            config.update_profile("Lif", "42", "", "", 2)
        with pytest.raises(ValueError):
            config.update_profile("Lif", "42", "a", "", 2)
        with pytest.raises(ValueError):
           config.update_profile("Lif", "42", "d", "a", -50)
        with pytest.raises(ValueError):
            config.rename_profile("","")
        with pytest.raises(ValueError):
            config.set_mask_color((22,12))
        with pytest.raises(ValueError):
            config.select_profile("")
        with pytest.raises(DeletionForbidden):
            config.delete_profile("Lif")
            config.delete_profile("Tif")
