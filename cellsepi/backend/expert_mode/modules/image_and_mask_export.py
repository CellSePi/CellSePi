import pathlib

from backend.constants import downloads_directory
from backend.data_util import FileTransfer
from backend.expert_mode.module import *


class ImageExportModule(Module, ABC):
    _gui_config = ModuleGuiConfig("ImageAndMaskExport",
                                  Categories.OUTPUTS,
                                  "This module handles the export of images and segmentation masks to a directory.")

    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.inputs = {
            "image_paths": InputPort("image_paths", dict, opt=True),
            "mask_paths": InputPort("mask_paths", dict, opt=True),
        }
        self.user_export_file_path: DirectoryPath = DirectoryPath(str(downloads_directory()))

    def run(self):
        image_paths = self.inputs["image_paths"].data

        first_series = next(iter(image_paths.values()))
        first_path = next(iter(first_series.values()))
        source_dir = pathlib.Path(first_path).parent
        target_dir = pathlib.Path(self.user_export_file_path.path)

        file_transfer = FileTransfer(
            event_manager=self.event_manager
        )

        if image_paths is not None:
            file_transfer(
                source_dir=source_dir,
                target_dir=target_dir,
            )