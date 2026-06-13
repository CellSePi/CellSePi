import os
from enum import auto

import numpy as np
from tifffile import tifffile

from backend.expert_mode.listener import ProgressEvent
from backend.expert_mode.module import *
from backend.expert_mode.pipeline_manager import PipelineRunningException


class ProjectionType(Enum):
    Z_MAX = auto()
    Z_MEAN = auto()


class Project3dTo2d(Module, ABC):
    _gui_config = ModuleGuiConfig(
        "Project3Dto2D",
        Categories.FILTERS,
        "This module handles the conversion from 3D data to 2D data based on a Z-maximum or Z-mean projection.")

    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)

        # ToDo EK: Currently compatibility of ports is evaluated based on the key in this dictionary.
        #  This effectively prevents multiple image_paths or mask_paths being connected to a single module
        self.inputs = {
            "image_paths": InputPort("image_paths", dict),
        }
        self.outputs = {
            "image_paths": OutputPort("image_paths", dict),
        }
        self.user_projection_type: ProjectionType = ProjectionType.Z_MAX

    def run(self):
        images = self.inputs["image_paths"].data
        outputs_images = {}
        n_series = len(images)
        self.event_manager.notify(
            ProgressEvent(
                percent=0,
                process=f"Projecting Series: Starting"
            )
        )
        for iN, series in enumerate(images):
            if self.is_cancelled():
                self.outputs["image_paths"].data = outputs_images
                self.event_manager.notify(
                    ProgressEvent(percent=int((iN) / n_series * 100), process="Projection: Cancelled"))
                return
            outputs_images[series] = {}
            for channel in images[series]:
                image_path = images[series][channel]
                image = tifffile.imread(image_path)  # dimensions are: Z,Y,X
                if image.ndim != 3:
                    raise PipelineRunningException("Value Error", "Wrong image format, expected a 3D image.")
                if self.user_projection_type == ProjectionType.Z_MAX:
                    projected = np.max(image, axis=0)
                    suffix = "_max"
                else:
                    projected = np.mean(image, axis=0).round().astype(image.dtype)
                    suffix = "_mean"

                base_dir = self.get_working_directory()
                name_without_type = os.path.splitext(os.path.basename(image_path))[0]

                new_filename = f"{name_without_type}{suffix}.tiff"
                new_path = os.path.join(base_dir, new_filename)

                tifffile.imwrite(new_path, projected)

                outputs_images[series][channel] = new_path

            self.event_manager.notify(
                ProgressEvent(
                    percent=int((iN + 1) / n_series * 100),
                    process=f"Projecting Series: {iN + 1}/{n_series}"
                )
            )
        self.outputs["image_paths"].data = outputs_images
        self.event_manager.notify(ProgressEvent(percent=100, process=f"Projecting Series: Finished"))
