from backend.data_util import load_directory, ReturnTypePath
from backend.expert_mode.module import *
from frontend.gui_directory import DirectoryCard


class ReadTif(Module,ABC):
    _gui_config = ModuleGuiConfig("ReadTif",Categories.INPUTS,"This module handles the read in of .tif/.tiff files and if available reads in the mask of the images.")
    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.outputs = {
            "image_paths": OutputPort("image_paths", dict),
            "mask_paths": OutputPort("mask_paths", dict),
        }
        self.user_directory_path: DirectoryPath = DirectoryPath()
        self.user_channel_prefix: str = "c"
        self.user_mask_suffix: str = "_seg"

    def run(self):
        working_directory = DirectoryCard().select_directory_parallel(self.user_directory_path.path, False, self.user_channel_prefix, self.event_manager)
        self.outputs["image_paths"].data,self.outputs["mask_paths"].data= load_directory(working_directory, self.user_channel_prefix, self.user_mask_suffix, ReturnTypePath.BOTH_PATHS, self.event_manager)