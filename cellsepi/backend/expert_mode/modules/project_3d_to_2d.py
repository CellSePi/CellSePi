import os

import numpy as np
from tifffile import tifffile
from PIL import Image

from backend.expert_mode.listener import ProgressEvent


class Project3dTo2d(Module, ABC):
    _gui_config = ModuleGuiConfig("Project3Dto2D",Categories.FILTERS,"This modules handles the conversion from 3D data to 2D data based on an max z projection.")
    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.inputs = {
            "image_paths": InputPort("image_paths", dict),
        }
        self.outputs = {
            "image_paths": OutputPort("image_paths", dict),
        }

    def run(self):
        images = self.inputs["image_paths"].data
        outputs_images = {}
        n_series = len(images)
        self.event_manager.notify(ProgressEvent(percent=0, process=f"Projecting Series: Starting"))
        for iN,series in enumerate(images):
            outputs_images[series] = {}
            for channel in images[series]:
                image_path = images[series][channel]
                image = tifffile.imread(image_path) #dimensions are: X, Y, Z
                image_max = np.max(image,axis=2)
                base_dir = os.path.dirname(image_path)
                proj_dir = os.path.join(base_dir, "projections")
                os.makedirs(proj_dir, exist_ok=True)
                name =os.path.basename(image_path)
                new_path = os.path.join(proj_dir, name)
                image_max_8bit = ((image_max - image_max.min()) / (image_max.max() - image_max.min()) * 255).astype(np.uint8)
                img8 = Image.fromarray(image_max_8bit)
                img8.save(new_path, format="TIFF")
                outputs_images[series][channel] = new_path

            self.event_manager.notify(ProgressEvent(percent=int((iN+1) / n_series * 100), process=f"Projecting Series: {iN+1}/{n_series}"))
        self.outputs["image_paths"].data = outputs_images
        self.event_manager.notify(ProgressEvent(percent=100, process=f"Projecting Series: Finished"))




