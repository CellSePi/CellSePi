import json
import pytest
from pydantic import ValidationError
from unittest.mock import patch, MagicMock
from backend.settings import SettingsManager, AppSettings, DataPersistenceConfig


@pytest.fixture(autouse=True)
def reset_settings_singleton():
    SettingsManager._instance = None
    yield
    SettingsManager._instance = None


@pytest.fixture
def mock_dir_manager(tmp_path):
    def fake_init(self, filename="settings.json"):
        self.file_path = tmp_path / filename
        self.settings = None
        self.load_settings()

    with patch.object(SettingsManager, '__init__', fake_init):
        yield tmp_path


def test_pydantic_validation():
    with pytest.raises(ValidationError):
        DataPersistenceConfig(cutoff=-5)


def test_load_settings_missing_file(mock_dir_manager):
    manager = SettingsManager(filename="test_settings.json")
    assert manager.settings.cache.cutoff == 3  # Standardwert


def test_save_and_load_settings(mock_dir_manager):
    manager = SettingsManager(filename="test_settings.json")
    manager.settings.cache.cutoff = 99
    manager.save_settings()

    manager.load_settings()
    assert manager.settings.cache.cutoff == 99


def test_load_corrupted_settings(mock_dir_manager, capsys):
    from backend.error_manager import ErrorManager

    file_path = mock_dir_manager / "corrupted_settings.json"
    file_path.write_text("{ broken json ]")

    with patch.object(ErrorManager, 'log') as mock_log:
        manager = SettingsManager(filename="corrupted_settings.json")

        assert manager.settings.cache.cutoff == 3
        mock_log.assert_called_once()


def test_rest_settings(mock_dir_manager):
    manager = SettingsManager()
    manager.settings.cache.cutoff = 999
    manager.rest_settings()
    assert manager.settings.cache.cutoff == 3

@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_async_methods(mock_dir_manager):
    manager = SettingsManager()

    manager.settings.cache.cutoff = 42
    await manager.save_settings_async()

    manager.settings.cache.cutoff = 0
    await manager.load_settings_async()
    assert manager.settings.cache.cutoff == 42

    await manager.reset_settings_async()
    assert manager.settings.cache.cutoff == 3