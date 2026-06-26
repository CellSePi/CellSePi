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
class ReadFiles(Module):
    _gui_config = ModuleGuiConfig("ReadFiles",Categories.INPUTS,"This module handles the read in of different files.")
    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.outputs = OutputPorts(
            OutputPort("image_paths", dict),
        )
        first_enum_member = list(FileSourceFileType)[0]
        self.user_file_path: FilePath = FilePath(suffix=first_enum_member.value.extensions)
        self.user_file_type = first_enum_member
        self.user_over_write = OverWrite.ALWAYS
        self.on_change_user_file_type = self.update_suffix

    def settings_init(self):
        self.update_suffix()

    def update_suffix(self):
        self.user_file_path.suffix = self.user_file_type.value.extensions
        self._settings.update()

    def run(self):
        overwrite = True if self.user_over_write == OverWrite.ALWAYS else False
        working_directory = DirectoryCard().select_directory(path=self.user_file_path.path, file_type=self.user_file_type.value.ref,
                                                             event_manager= self.event_manager,overwrite=overwrite)
        self.outputs.image_paths.data= load_directory(directory=working_directory,return_type=ReturnTypePath.IMAGE_PATHS,event_manager= self.event_manager)