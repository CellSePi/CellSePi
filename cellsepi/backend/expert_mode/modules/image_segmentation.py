from backend.main_window import PipelineRunningException
from backend.main_window import BatchImageSegmentation


class ImageSegmentationModule(Module, ABC):
    _gui_config = ModuleGuiConfig("ImageSegmentation",Categories.SEGMENTATION,"This module handles the segmentation of cells for each series on the given segmentation_channel with the provided model in model_path.")
    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.inputs = {
            "image_paths": InputPort("image_paths", dict),
            "mask_paths": InputPort("mask_paths", dict,opt=True),
        }
        self.outputs = {
            "mask_paths": OutputPort("mask_paths", dict),
        }
        self.user_model_path: FilePath = FilePath()
        self.user_segmentation_channel: str = "2"
        self.user_diameter: float = 125.0
        self.user_mask_suffix: str = "_seg"

    def run(self):
        if self.inputs["mask_paths"].data is None:
            self.inputs["mask_paths"].data = {}
        try:
            BatchImageSegmentation(segmentation_channel=self.user_segmentation_channel,diameter=self.user_diameter,suffix=self.user_mask_suffix).run(self.event_manager,self.inputs["image_paths"].data,self.inputs["mask_paths"].data,self.user_model_path.path)
        except:
            raise PipelineRunningException("Segmentation Error", "Incompatible file for the segmentation model.")

        self.outputs["mask_paths"].data = self.inputs["mask_paths"].data

