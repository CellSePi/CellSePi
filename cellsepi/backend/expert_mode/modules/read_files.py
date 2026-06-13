from backend.data_util import load_directory, ReturnTypePath
from backend.constants import FileType, create_enum_subset, SourceType, OverWrite
from frontend.gui_directory import DirectoryCard
from backend.expert_mode.module import *

FileSourceFileType = create_enum_subset(
    "DirectoryFileType",
    FileType,
    lambda m: m.value.source == SourceType.FILE,
    fields_to_copy=["name", "extensions"]
)
class ReadFiles(Module,ABC):
    _gui_config = ModuleGuiConfig("ReadFiles",Categories.INPUTS,"This module handles the read in of different files.")
    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.outputs = {
            "image_paths": OutputPort("image_paths", dict),
        }
        first_enum_member = list(FileSourceFileType)[0]
        self.user_file_path: FilePath = FilePath(suffix=first_enum_member.value.extensions)
        self.user_file_type = first_enum_member
        self.user_over_write = OverWrite.ALWAYS
        self.user_channel_prefix: str = "c"
        self.user_mask_suffix: str = "_seg"

    @property
    def settings(self) -> ft.Stack | None:
        if self._settings is not None and self.update_suffix() is None:
            self.on_change_user_file_type = self.update_suffix
            self.user_file_path.suffix = self.user_file_type.value.extensions
        return self._settings

    def update_suffix(self):
        self.user_file_path.suffix = self.user_file_type.value.extensions

    def run(self):
        overwrite = True if self.user_over_write == OverWrite.ALWAYS else False
        working_directory = DirectoryCard().select_directory(self.user_file_path.path, self.user_file_type.value.ref,
                                                             self.user_channel_prefix,self.user_mask_suffix, self.event_manager,overwrite)
        self.outputs["image_paths"].data= load_directory(directory=working_directory, mask_suffix=self.user_mask_suffix,return_type=ReturnTypePath.IMAGE_PATHS,event_manager= self.event_manager)