from enum import Enum, auto
from pathlib import Path
from types import SimpleNamespace

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
