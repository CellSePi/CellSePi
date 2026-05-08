from backend.data_util import load_directory, ReturnTypePath
from frontend.gui_directory import DirectoryCard
from backend.expert_mode.module import *

class ReadLif(Module,ABC):
    _gui_config = ModuleGuiConfig("ReadLif",Categories.INPUTS,"This module handles the read in of .lif files and if available reads in the mask of the images.")
    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.outputs = {
            "image_paths": OutputPort("image_paths", dict),
            "mask_paths": OutputPort("mask_paths", dict),
        }
        self.user_file_path: FilePath = FilePath(suffix=["lif"])
        self.user_channel_prefix: str = "c"
        self.user_mask_suffix: str = "_seg"

    def run(self):
        working_directory = DirectoryCard().select_directory_parallel(self.user_file_path.path, True, self.user_channel_prefix, self.event_manager)
        self.outputs["image_paths"].data,self.outputs["mask_paths"].data= load_directory(working_directory, self.user_channel_prefix, self.user_mask_suffix, ReturnTypePath.BOTH_PATHS, self.event_manager)