from backend.main_window import BatchImageReadout


class ImageReadoutModule(Module, ABC):
    _gui_config = ModuleGuiConfig("ImageReadout",Categories.OUTPUTS,"This module handles the readout of the segmented images and saves them in an .xlsx file.")
    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.inputs = {
            "image_paths": InputPort("image_paths", dict),
            "mask_paths": InputPort("mask_paths", dict),
        }
        self.user_directory_path: DirectoryPath = DirectoryPath()
        self.user_segmentation_channel: str = "2"
        self.user_channel_prefix: str = "c"

    def run(self):
        BatchImageReadout(self.inputs["image_paths"].data, self.inputs["mask_paths"].data,self.user_segmentation_channel,self.user_channel_prefix,self.user_directory_path.path,True).run(self.event_manager)