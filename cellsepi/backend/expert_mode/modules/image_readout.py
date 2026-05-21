import pathlib

from backend.constants import ExportFileType, APP_DIR
from backend.fluorescence import BatchImageReadout
from backend.expert_mode.module import *


class ImageReadoutModule(Module, ABC):
    _gui_config = ModuleGuiConfig("ImageReadout",
                                  Categories.OUTPUTS,
                                  "This module handles the readout of the segmented images and saves them in an .xlsx file.")

    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.inputs = {
            "image_paths": InputPort("image_paths", dict),
            "mask_paths": InputPort("mask_paths", dict),
        }
        readout_dir = APP_DIR / "readout"
        readout_dir.mkdir(parents=True, exist_ok=True)
        self.user_export_directory_path: DirectoryPath = DirectoryPath(str(readout_dir))
        self.user_export_file_name: str = "fluorescence_readout"
        self.user_export_file_type: ExportFileType = ExportFileType.EXCEL
        self.user_segmentation_channel: str = "2"
        self.user_channel_prefix: str = "c"

    def run(self):
        path_with_new_suffix = pathlib.Path(pathlib.Path(self.user_export_directory_path.path) / self.user_export_file_name).with_suffix(self.user_export_file_type.value.extension)
        (BatchImageReadout(
            self.inputs["image_paths"].data,
            self.inputs["mask_paths"].data,
            self.user_export_file_type,
            path_with_new_suffix,
            self.user_segmentation_channel,
            self.user_channel_prefix,
            True)
         .run(self.event_manager))
