from backend.data_util import load_directory, ReturnTypePath
from backend.expert_mode.module import *
from backend.constants import SourceType, create_enum_subset, FileType, OverWrite
from frontend.gui_directory import DirectoryCard

DirectorySourceFileType = create_enum_subset(
    "DirectoryFileType",
    FileType,
    lambda m: m.value.source == SourceType.DIRECTORY,
    fields_to_copy=["name"]
)

class ReadDir(Module,ABC):
    _gui_config = ModuleGuiConfig("ReadDir",Categories.INPUTS,"This module handles the read in of a directory and if available reads in the mask of the images.")
    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.outputs = {
            "image_paths": OutputPort("image_paths", dict),
            "mask_paths": OutputPort("mask_paths", dict),
        }
        self.user_directory_path: DirectoryPath = DirectoryPath()
        first_enum_member = list(DirectorySourceFileType)[0]
        self.user_dir_type = first_enum_member
        self.user_over_write = OverWrite.ALWAYS
        self.user_channel_prefix: str = "c"
        self.user_mask_suffix: str = "_seg"

    def run(self):
        overwrite = True if self.user_over_write == OverWrite.ALWAYS else False
        working_directory = DirectoryCard().select_directory(self.user_directory_path.path, self.user_dir_type.value.ref, self.user_channel_prefix,self.user_mask_suffix, self.event_manager,overwrite)
        self.outputs["image_paths"].data,self.outputs["mask_paths"].data= load_directory(directory=working_directory,mask_suffix=self.user_mask_suffix,return_type=ReturnTypePath.BOTH_PATHS, event_manager=self.event_manager)