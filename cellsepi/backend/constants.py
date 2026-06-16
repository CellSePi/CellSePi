from enum import Enum, auto
from types import SimpleNamespace
from pathlib import Path
from typing import Optional, Callable

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


class ModelType(Enum):
    CP_SAM = SimpleNamespace(name= "CP Sam")
    CP_CYTO = SimpleNamespace(name= "CP Cyto")
    CP_NUCLEI = SimpleNamespace(name= "CP Nuclei")
    CUSTOM = SimpleNamespace(name= "Custom")


FILTER_FLOAT = r"^[0-9]*([.,][0-9]*)?$"
FILTER_INT = r"^[0-9]*$"
FILTER_SCIENTIFIC_FLOAT= r"^[0-9]*[.,]?[0-9]*([eE][-+]?[0-9]*)?$"
FILTER_FLOAT_0_TO_1 = r"^(0([.,][0-9]*)?|1([.,]0*)?|[.,][0-9]*|)$"

class FileType(Enum):
    LIF = SimpleNamespace(name="Lif", extensions=["lif"], source=SourceType.FILE)
    ND2 = SimpleNamespace(name="ND2", extensions=["nd2"], source=SourceType.FILE)
    ND2_DIR = SimpleNamespace(name="ND2 Dir", extensions=["nd2"], source=SourceType.DIRECTORY)
    CZI = SimpleNamespace(name="CZI", extensions=["czi"], source=SourceType.FILE)
    OME_TIFF = SimpleNamespace(name="OME-TIFF", extensions=["ome.tiff", "ome.tif"], source=SourceType.FILE)
    TIFF_DIR = SimpleNamespace(name="TIFF Dir", extensions=["tiff", "tif"], source=SourceType.DIRECTORY)

    @property
    def extension_string(self):
        formatted_extension = [f".{ext}" for ext in self.value.extensions]
        if len(formatted_extension) == 0:
            return ""
        if len(formatted_extension) == 1:
            return formatted_extension[0]

        return ", ".join(formatted_extension[:-1]) + " or " + formatted_extension[-1]

class OverWrite(Enum):
    ALWAYS = auto()
    NEVER = auto()

def create_enum_subset(new_name: str, base_enum: type[Enum], condition_func: Callable, fields_to_copy: list[str]) -> type[Enum]:
    members = {}
    for enum_key, member in base_enum.__members__.items():
        if condition_func(member):
            namespace_kwargs = {"ref": member}
            for field in fields_to_copy:
                if hasattr(member.value, field):
                    namespace_kwargs[field] = getattr(member.value, field)
            members[enum_key] = SimpleNamespace(**namespace_kwargs)

    return Enum(new_name, members)

class ExportFileType(Enum):
    EXCEL = SimpleNamespace(name="EXCEL", extension=".xlsx", seperator=None)
    TSV = SimpleNamespace(name="TSV", extension=".tsv", seperator="\t")
    CSV = SimpleNamespace(name="CSV", extension=".csv", seperator=",")
    PDF = SimpleNamespace(name="PDF", extension=".pdf", seperator=None)


class Suffixes(Enum):
    SEGMENTATION_MASK = SimpleNamespace(name="SEGMENTATION_MASK", suffixes=["_seq"], extensions=["npy"])
    SPOT_MASK = SimpleNamespace(name="SPOT_MASK", suffixes=["_sdm"], extensions=["npy"])


class DownscaleMode(str, Enum):
    NONE = "Disabled"
    PIXELS = "Pixels"
    FRACTION = "Fraction"


def downloads_directory() -> Path:
    home = Path.home()
    downloads_dir = home / "Downloads"
    return downloads_dir
