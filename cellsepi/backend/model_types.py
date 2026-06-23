from enum import Enum, auto
from types import SimpleNamespace

class ModelType(Enum):
    CP_SAM = SimpleNamespace(name= "Cellpose SAM")
    CP_SAM_V2 = SimpleNamespace(name= "Cellpose SAM v2")
    CP_DINO = SimpleNamespace(name= "Cellpose DINO")
    CP_SMALL_DINO = SimpleNamespace(name= "Cellpose Small DINO")
    CP_CYTO = SimpleNamespace(name= "Cellpose Cyto")
    CP_NUCLEI = SimpleNamespace(name= "Cellpose Nuclei")
    CUSTOM = SimpleNamespace(name= "Custom")
