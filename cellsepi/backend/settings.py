import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

import anyio
from pydantic import BaseModel, Field

from backend.constants import DownscaleMode

# Setup individual settings
class DataPersistenceConfig(BaseModel):
    cutoff: int = Field(default=3, ge=0)


@dataclass
class SettingsOption:
    name: str
    opt_type: type
    default: Any
    hint: str = ""


# Define nested configuration schemas
class SegmentationConfig(BaseModel):
    mode: DownscaleMode = DownscaleMode.PIXELS  # SettingsOption("Downscale Mode", DownscaleMode.PIXELS, hint="Whether to use the original image, a fixed downscaling (pixels) or a relative downscaling (fraction).")
    max_pixels: int = Field(default=512, ge=10, le=10000)
    max_fraction: float = Field(default=0.25, ge=0.0, le=1.0)



class VisualizationConfig(BaseModel):
    mode: DownscaleMode = DownscaleMode.PIXELS
    max_pixels: int = Field(default=1024, ge=10, le=10000)
    max_fraction: float = Field(default=0.25, ge=0.0, le=1.0)


class PerformanceConfig(BaseModel):
    segmentation_downscaling: SegmentationConfig = Field(default_factory=SegmentationConfig)
    visualization_downscaling: VisualizationConfig = Field(default_factory=VisualizationConfig)

class SegmentationRunConfig(BaseModel):
    delete_small_masks: bool = False
    mask_deletion_diameter: float = Field(default=0.00, ge=0.0)  #segmented mask smaller than this diameter deletes the mask



class ImageNormalizationConfig(BaseModel):
    normalize_gallery: bool = True
    margin: float = Field(default=0.01, ge=0.0, le=1.0)  # The distance to the image border to ignore in percent of image width (0.2 means that 20% of the image width and height is ignored on each side (total 40% per side))
    upper_quantile: float = Field(default=0.99, ge=0.0, le=1.0)  # The value to consider as maximum for the image inside the margin
    lower_quantile: float = Field(default=0.02, ge=0.0, le=1.0)  # The value to consider as minimum for the image inside the margin


# Define main Settings Schema with built-in defaults


class AppSettings(BaseModel):
    cache: DataPersistenceConfig = Field(default_factory=DataPersistenceConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    image: ImageNormalizationConfig = Field(default_factory=ImageNormalizationConfig)
    segmentation: SegmentationRunConfig = Field(default_factory=SegmentationRunConfig)


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

    def rest_settings(self):
        self.settings = AppSettings()

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

    async def reset_settings_async(self):
        return await anyio.to_thread.run_sync(self.rest_settings)

