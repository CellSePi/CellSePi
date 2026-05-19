from enum import Enum
from types import SimpleNamespace


class ExportFileType(Enum):
    EXCEL = SimpleNamespace({"name": "EXCEL", "extension": ".xlsx", "seperator": None})
    TSV = SimpleNamespace({"name": "TSV", "extension": ".tsv", "seperator": "\t"})
    CSV = SimpleNamespace({"name": "CSV", "extension": ".csv", "seperator": ","})
    PDF = SimpleNamespace({"name": "PDF", "extension": ".pdf", "seperator": None})
