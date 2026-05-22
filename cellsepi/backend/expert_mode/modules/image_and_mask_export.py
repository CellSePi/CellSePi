import os
import pathlib
from typing import Iterable

from backend.constants import ExportFileType
from backend.data_util import FileTransfer
from backend.fluorescence import BatchImageReadout
from backend.expert_mode.module import *


class ImageReadoutModule(Module, ABC):
    _gui_config = ModuleGuiConfig("ImageAndMaskExport",
                                  Categories.OUTPUTS,
                                  "This module handles the export of images and segmentation masks to a directory.")

    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.inputs = {
            "image_paths": InputPort("image_paths", dict, opt=True),
            "mask_paths": InputPort("mask_paths", dict, opt=True),
        }
        self.user_export_file_path: DirectoryPath = DirectoryPath("fluorescence_readout.xlsx")

    def run(self):
        def to_posix_path(path: str | pathlib.Path | Iterable[str | pathlib.Path]):
            def to_posix(path: str | pathlib.Path) -> str:
                return pathlib.Path(os.path.normpath(path).replace("\\", "/"))
            if isinstance(path, Iterable):
                return [to_posix(p) for p in path]

            return to_posix(path)

        # ToDo Verify functionality
        image_paths = self.inputs["image_paths"].data
        mask_paths = self.inputs["mask_paths"].data

        target_dir = self.user_export_file_path.path
        target_dir = pathlib.Path(target_dir)
        ft = FileTransfer(
            event_manager=self.event_manager
        )
        if image_paths is not None:
            ft(
                source_paths=to_posix_path(image_paths),
                target_dir=target_dir,
            )
        if mask_paths is not None:
            ft(
                source_paths=to_posix_path(mask_paths),
                target_dir=target_dir,
            )
