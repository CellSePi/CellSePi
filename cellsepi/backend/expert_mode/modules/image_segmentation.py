import os

import pickle

from backend.expert_mode.limits import Limit
from backend.expert_mode.pipeline_manager import PipelineRunningException
from backend.segmentation import BatchImageSegmentation
from backend.expert_mode.module import *
from backend.constants import ModelType


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
        self.user_model_type: ModelType = ModelType.CUSTOM
        self.user_model_path: FilePath = FilePath()
        self.user_segmentation_channel: str = "2"
        self.user_diameter: float = 125.00
        self.limit_diameter: Limit = Limit(min_val=0.00)
        self.user_mask_suffix: str = "_seg"
        self.user_overwrite_existing_masks: bool = False

    @property
    def settings(self) -> ft.Stack | None:
        if self._settings is not None and self.on_change_user_model_type() is None:
            self.on_change_user_model_type = self.update_model_path_activation
            self.ref_user_model_path.animate_opacity=600
            if self.user_model_type is ModelType.CUSTOM:
                self.ref_user_model_path.current.opacity = 1
            else:
                self.ref_user_model_path.current.opacity = 0
        return self._settings

    def update_model_path_activation(self):
        if self.user_model_type is ModelType.CUSTOM:
            self.ref_user_model_path.current.opacity = 1
            self._settings.update()
        else:
            self.ref_user_model_path.current.opacity = 0
            self._settings.update()

    def run(self):
        if self.inputs["mask_paths"].data is None:
            self.inputs["mask_paths"].data = {}
        else:
            masks = self.inputs["mask_paths"].data
            if self.user_overwrite_existing_masks:
                for img in masks:
                    path = masks[img][self.user_segmentation_channel]
                    if os.path.exists(path):
                        os.remove(path)
                    masks[img].pop(self.user_segmentation_channel, None)

        try:
            BatchImageSegmentation(segmentation_channel=self.user_segmentation_channel,diameter=self.user_diameter,suffix=self.user_mask_suffix).run(self.event_manager,self.inputs["image_paths"].data,self.inputs["mask_paths"].data,self.user_model_path.path,model_type=self.user_model_type)
        except pickle.UnpicklingError as ex:
            raise PipelineRunningException("Segmentation Error", "Invalid or corrupted file. Please select a valid model.")

        self.outputs["mask_paths"].data = self.inputs["mask_paths"].data

