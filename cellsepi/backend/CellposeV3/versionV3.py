# -*- coding: utf-8 -*-

# ---------------------------------------------------------------------------
# This file contains code from the "cellpose" Python package.
# Original source: https://github.com/mouseland/cellpose
#
# Author: Carsen Stringer and Marius Pachitariu.
# Copyright © 2023 Howard Hughes Medical Institute.
# License: BSD 3-Clause.
# See the file 'CELLPOSE_LICENSE' in this directory or:
# https://github.com/MouseLand/cellpose/blob/main/LICENSE
# ---------------------------------------------------------------------------

from importlib.metadata import PackageNotFoundError, version
import sys
from platform import python_version
import torch

try:
    version = version("cellpose")
except PackageNotFoundError:
    version = "unknown"

version_str = f"""
cellpose version: \t{version} 
platform:       \t{sys.platform} 
python version: \t{python_version()} 
torch version:  \t{torch.__version__}"""
