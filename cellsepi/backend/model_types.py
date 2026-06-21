from enum import Enum, auto
from types import SimpleNamespace

class ModelType(Enum):
    CP_SAM = SimpleNamespace(name= "CP Sam")
    CP_CYTO = SimpleNamespace(name= "CP Cyto")
    CP_NUCLEI = SimpleNamespace(name= "CP Nuclei")
    CUSTOM = SimpleNamespace(name= "Custom")
