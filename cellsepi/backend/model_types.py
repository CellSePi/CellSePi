from enum import Enum, auto
from types import SimpleNamespace

class ModelType(Enum):
    CP_SAM = SimpleNamespace(name= "CP Sam")
    CP_SAM_V2 = SimpleNamespace(name= "CP Sam v2")
    CP_DINO = SimpleNamespace(name= "CP Dino")
    CP_SMALL_DINO = SimpleNamespace(name= "CP Small Dino")
    CP_CYTO = SimpleNamespace(name= "CP Cyto")
    CP_NUCLEI = SimpleNamespace(name= "CP Nuclei")
    CUSTOM = SimpleNamespace(name= "Custom")
