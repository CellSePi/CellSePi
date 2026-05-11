import os
import shutil
from enum import Enum, auto
from types import SimpleNamespace
from pathlib import Path
from typing import Optional


class ReturnTypePath(Enum):
    IMAGE_PATHS = auto()
    MASK_PATHS = auto()
    BOTH_PATHS = auto()


class SourceType(Enum):
    FILE = auto()
    DIRECTORY = auto()


class FileType(Enum):
    LIF = SimpleNamespace({"name": "Lif", "extensions": ["lif"], "source": SourceType.FILE})
    ND2 = SimpleNamespace({"name": "ND2", "extensions": ["nd2"], "source": SourceType.FILE})
    CZI = SimpleNamespace({"name": "CZI", "extensions": ["czi"], "source": SourceType.FILE})
    TIFF = SimpleNamespace({"name": "TIFF/TIF", "extensions": ["tiff", "tif"], "source": SourceType.DIRECTORY})


class DirectoryManager:
    """
    Manages project directories and intermediate file storage.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        base_path = Path.home() / ".cellsepi"
        self._base_path = Path(base_path)
        self._cache_path: Optional[Path] = None

    @property
    def base_directory(self) -> Path:
        return self._base_path

    @property
    def cache_directory(self) -> Path:
        """
        Returns the path for intermediate files, creating it if it doesn't exist.
        """
        if self._cache_path is None:
            self._cache_path = self._base_path / "cache"
            self._cache_path.mkdir(parents=True, exist_ok=True)

        return self._cache_path

    def get_cache_file_path(self, filename: str) -> Path:
        """
        Returns a full path for a file within the intermediate directory.
        """
        # Accessing the property ensures the directory is created
        dir_path = Path(self.cache_directory.path)
        return dir_path / filename

    def get_cache_dir_path(self, dirname: str) -> Path:
        dirpath = self.cache_directory / dirname
        os.makedirs(dirpath, exist_ok=True)
        return dirpath

    def cleanup_cache(self):
        """
        Removes all files in the intermediate directory.
        """
        if self._cache_path and self._cache_path.exists():
            for item in self._cache_path.glob("*"):

                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
