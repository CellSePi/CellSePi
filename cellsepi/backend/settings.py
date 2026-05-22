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
from dataclasses import dataclass
from enum import Enum
from typing import Any

import anyio
from pydantic import BaseModel, Field


class DownscaleMode(str, Enum):
    NONE = "none"
    PIXELS = "pixels"
    FRACTION = "fraction"


# Setup individual settings
class DataPersistenceConfig(BaseModel):
    cutoff: int = 3


@dataclass
class SettingsOption:
    name: str
    opt_type: type
    default: Any
    hint: str = ""


# Define nested configuration schemas
class SegmentationConfig(BaseModel):
    mode: DownscaleMode = DownscaleMode.PIXELS  # SettingsOption("Downscale Mode", DownscaleMode.PIXELS, hint="Whether to use the original image, a fixed downscaling (pixels) or a relative downscaling (fraction).")
    max_pixels: int = 512
    max_fraction: float = 0.25


class VisualizationConfig(BaseModel):
    mode: DownscaleMode = DownscaleMode.PIXELS
    max_pixels: int = 1024
    max_fraction: float = 0.25


class PerformanceConfig(BaseModel):
    segmentation: SegmentationConfig = Field(default_factory=SegmentationConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)


class ImageNormalizationConfig(BaseModel):
    normalize_gallery: bool = True
    margin: float = 0.1  # The distance to the image border to ignore in percent of image width (0.2 means that 20% of the image width and height is ignored on each side (total 40% per side))
    upper_quantile: float = 0.99  # The value to consider as maximum for the image inside the margin
    lower_quantile: float = 0.02  # The value to consider as minimum for the image inside the margin


# Define main Settings Schema with built-in defaults


class AppSettings(BaseModel):
    cache: DataPersistenceConfig = Field(default_factory=DataPersistenceConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    image: ImageNormalizationConfig = Field(default_factory=ImageNormalizationConfig)


# Manage the File I/O wrapping the schema
class SettingsManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, filename="settings.json"):
        from backend.data_util import DirectoryManager
        self.file_path = DirectoryManager().base_directory / filename
        self.settings: AppSettings = None

        self.load_settings()

    def load_settings(self) -> AppSettings:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                settings = AppSettings.model_validate(data)
            except Exception as e:
                print(f"Invalid settings file ({e}). Falling back to defaults.")
                settings = AppSettings()
        else:
            settings = AppSettings()

        self.settings = settings
        return settings

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
