import json
import pathlib

# from backend.constants import DirectoryManager
#
# DEFAULT_SETTINGS = {
#     "cache": {
#         "cutoff": 3
#     },
#     "performance": {
#         "segmentation": {
#             "max_pixels": 512,
#             "max_fraction": 0.25,
#             "fraction_or_pixels": "pixels"
#         },
#         "visualization": {
#             "max_pixels": 512,
#             "max_fraction": 0.25,
#             "fraction_or_pixels": "pixels"
#         }
#     }
# }
#
#
# def compare_dicts(dict1, dict2) -> bool:
#     """
#     Compares two dictionaries regarding key and value type equality.
#     """
#     for key1 in dict1:
#         if key1 not in dict2:
#             return False
#         if type(dict1[key1]) != type(dict2[key1]):
#             return False
#         if type(dict1[key1]) == dict:
#             if not compare_dicts(dict1[key1], dict2[key1]):
#                 return False
#     return True
#
#
# class SettingsFile:
#
#     def __init__(self, filename="settings.json"):
#         self.file_path = DirectoryManager().base_directory / filename
#
#         self._settings = self.load_settings()
#
#     def load_settings(self):
#         if self.file_path.exists():
#             with open(self.file_path, "r") as f:
#                 data = json.load(f)
#         else:
#             data = DEFAULT_SETTINGS
#
#             if not compare_dicts(data, DEFAULT_SETTINGS):
#                 data = DEFAULT_SETTINGS
#
#         self._settings = data
#
#         self.populate_settings()
#
#     def save_settings(self):
#         with open(self.file_path, "w") as f:
#             json.dump(self._settings, f, indent=4)


import json
from pathlib import Path
from typing import Literal

import anyio
from pydantic import BaseModel, Field

from backend.constants import DirectoryManager


class DataPersistenceConfig(BaseModel):
    cutoff: int = 3

# Define nested configuration schemas
class SegmentationConfig(BaseModel):
    mode: Literal["pixels", "fraction"] | None = "pixels"
    max_pixels: int = 512
    max_fraction: float = 0.25


class VisualizationConfig(BaseModel):
    mode: Literal["pixels", "fraction"] | None = "pixels"
    max_pixels: int = 1024
    max_fraction: float = 0.25


class PerformanceConfig(BaseModel):
    segmentation: SegmentationConfig = Field(default_factory=SegmentationConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)





# Define main Settings Schema with built-in defaults
class AppSettings(BaseModel):
    cache: DataPersistenceConfig = Field(default_factory=DataPersistenceConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)


# Manage the File I/O wrapping the schema
class SettingsManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, filename="settings.json"):
        self.file_path = DirectoryManager().base_directory / filename
        self.settings: AppSettings = self.load_settings()

    def load_settings(self) -> AppSettings:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                return AppSettings.model_validate(data)
            except Exception as e:
                print(f"Invalid settings file ({e}). Falling back to defaults.")
                return AppSettings()
        else:
            return AppSettings()

    def save_settings(self):
        with open(self.file_path, "w") as f:
            # Serializes the object back into clean JSON
            f.write(self.settings.model_dump_json(indent=4))

    async def load_settings_async(self) -> AppSettings:
        """Loads settings on a background worker thread."""
        return await anyio.to_thread.run_sync(self.load_settings)

    async def save_settings_async(self):
        """Saves settings on a background worker thread without blocking the GUI."""
        return await anyio.to_thread.run_sync(self.save_settings)
