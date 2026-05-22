import os
import shutil
from enum import Enum, auto
from types import SimpleNamespace
from pathlib import Path
from typing import Optional

BIT_DEPTH = 16

CSP_CHANNEL_PREFIX = "_CSP-channel-pref_"

APP_NAME = ".cellsepi"
APP_DIR = Path(Path.home() / APP_NAME)



class ReturnTypePath(Enum):
    IMAGE_PATHS = auto()
    MASK_PATHS = auto()
    BOTH_PATHS = auto()


class SourceType(Enum):
    FILE = auto()
    DIRECTORY = auto()


class FileType(Enum):
    LIF = SimpleNamespace(name="Lif", extensions=["lif"], source=SourceType.FILE)
    ND2 = SimpleNamespace(name="ND2", extensions=["nd2"], source=SourceType.FILE)
    ND2_DIR = SimpleNamespace(name="ND2 Dir", extensions=["nd2"], source=SourceType.DIRECTORY)
    CZI = SimpleNamespace(name="CZI", extensions=["czi"], source=SourceType.FILE)
    OME_TIFF = SimpleNamespace(name="OME-TIFF", extensions=["ome.tiff", "ome.tif"], source=SourceType.FILE)
    TIFF_DIR = SimpleNamespace(name="TIFF Dir", extensions=["tiff", "tif"], source=SourceType.DIRECTORY)



class ExportFileType(Enum):
    EXCEL = SimpleNamespace(name="EXCEL", extension=".xlsx", seperator=None)
    TSV = SimpleNamespace(name="TSV", extension=".tsv", seperator="\t")
    CSV = SimpleNamespace(name="CSV", extension=".csv", seperator=",")
    PDF = SimpleNamespace(name="PDF", extension=".pdf", seperator=None)



class Suffixes(Enum):
    SEGMENTATION_MASK = SimpleNamespace(name="SEGMENTATION_MASK", suffixes=["_seq"], extensions=["npy"])
    SPOT_MASK = SimpleNamespace(name="SPOT_MASK", suffixes=["_sdm"], extensions=["npy"])


class DirectoryManager:
    """
    Manages project directories and intermediate file storage.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app_dir=None):
        if app_dir is None:
            app_dir = APP_DIR
        self._base_path = Path(app_dir)
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

    def get_cache_dir_path(self, dirname: str, makedir=True) -> Path:
        dirpath = self.cache_directory / dirname

        if makedir:
            os.makedirs(dirpath, exist_ok=True)
        return dirpath

    def streamline_cache(self):
        """
        Removes only the old entries in the cache directory.
        Keeps the three most recent directories.
        """
        if self.cache_directory and self.cache_directory.exists():
            modification_times = []
            for item in self._cache_path.glob("*"):
                if item.is_dir():
                    modification_times.append([item, item.stat().st_mtime])

            print(modification_times)
            modification_times = sorted(modification_times, key=lambda elem: elem[1], reverse=True)
            for elem in modification_times[3:]:
                item = elem[0]
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

            pass

        def clear_cache(self):
            """
            Removes all files in the cache directory.
            """
            if self.cache_directory and self.cache_directory.exists():
                for item in self._cache_path.glob("*"):

                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

    @staticmethod
    def downloads_directory() -> Path:
        home = Path.home()
        downloads_dir = home / "Downloads"
        return downloads_dir
