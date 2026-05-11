from enum import Enum, auto
from types import SimpleNamespace


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
