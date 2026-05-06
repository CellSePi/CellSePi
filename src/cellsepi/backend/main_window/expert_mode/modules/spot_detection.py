import os
from pathlib import Path

from cellsepi.backend.main_window.expert_mode.modules.big_fish import  detect_spots
import numpy as np
import tifffile
from scipy.ndimage import binary_dilation

from cellsepi.backend.main_window.expert_mode.listener import ProgressEvent
from cellsepi.backend.main_window.expert_mode.module import *
from cellsepi.backend.main_window.expert_mode.pipeline_manager import PipelineRunningException


class SpotDetectionModule(Module, ABC):
    _gui_config = ModuleGuiConfig("SpotDetection",Categories.SEGMENTATION,"This module handles spot detection in cells for each series on the given segmentation_channel with the big-fish python package.")
    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.inputs = {
            "image_paths": InputPort("image_paths", dict),
            "mask_paths": InputPort("mask_paths", dict,opt=True),
        }
        self.outputs = {
            "mask_paths": OutputPort("mask_paths", dict),
        }
        self.user_remove_duplicate:bool = True
        self.user_use_threshold: bool = False
        self.user_use_log_kernel_and_minimum_distance:bool = False
        self.user_segmentation_channel: str = "2"
        self.user_mask_suffix: str = "_sdm" #spot detection mask
        self.user_mask_spot_radius_pixels: float = 3.0
        self.user_threshold: float = 355.0
        self.user_log_kernel_x_pixels: float = 1.456
        self.user_log_kernel_y_pixels: float = 1.456
        self.user_log_kernel_z_pixels: float = 1.167
        self.user_minimum_distance_x_pixels: float = 1.456
        self.user_minimum_distance_y_pixels: float = 1.456
        self.user_minimum_distance_z_pixels: float = 1.167
        self.user_voxel_size_x_nm: float = 103.0
        self.user_voxel_size_y_nm: float = 103.0
        self.user_voxel_size_z_nm: float = 300.0
        self.user_spot_radius_x_nm: float = 150.0
        self.user_spot_radius_y_nm: float = 150.0
        self.user_spot_radius_z_nm: float = 350.0

    @property
    def settings(self) -> ft.Stack|None:
        if self._settings is not None and self.on_change_user_use_log_kernel_and_minimum_distance() is None:
            self.on_change_user_use_log_kernel_and_minimum_distance = self.update_disable_kernel_distance
            self.on_change_user_use_threshold = self.update_disable_threshold
            self.update_disable_kernel_distance()
            self.update_disable_threshold()
        return self._settings

    def update_disable_threshold(self):
        if self.user_use_threshold:
            self.ref_user_threshold.current.disabled = False
        else:
            self.ref_user_threshold.current.disabled = True

    def update_disable_kernel_distance(self):
        if self.user_use_log_kernel_and_minimum_distance:
            self.ref_user_voxel_size_x_nm.current.disabled = True
            self.ref_user_voxel_size_y_nm.current.disabled = True
            self.ref_user_voxel_size_z_nm.current.disabled = True
            self.ref_user_spot_radius_x_nm.current.disabled = True
            self.ref_user_spot_radius_y_nm.current.disabled = True
            self.ref_user_spot_radius_z_nm.current.disabled = True
            self.ref_user_log_kernel_x_pixels.current.disabled = False
            self.ref_user_log_kernel_y_pixels.current.disabled = False
            self.ref_user_log_kernel_z_pixels.current.disabled = False
            self.ref_user_minimum_distance_x_pixels.current.disabled = False
            self.ref_user_minimum_distance_y_pixels.current.disabled = False
            self.ref_user_minimum_distance_z_pixels.current.disabled = False
        else:
            self.ref_user_voxel_size_x_nm.current.disabled = False
            self.ref_user_voxel_size_y_nm.current.disabled = False
            self.ref_user_voxel_size_z_nm.current.disabled = False
            self.ref_user_spot_radius_x_nm.current.disabled = False
            self.ref_user_spot_radius_y_nm.current.disabled = False
            self.ref_user_spot_radius_z_nm.current.disabled = False
            self.ref_user_log_kernel_x_pixels.current.disabled = True
            self.ref_user_log_kernel_y_pixels.current.disabled = True
            self.ref_user_log_kernel_z_pixels.current.disabled = True
            self.ref_user_minimum_distance_x_pixels.current.disabled = True
            self.ref_user_minimum_distance_y_pixels.current.disabled = True
            self.ref_user_minimum_distance_z_pixels.current.disabled = True

    def run(self):
        mask_paths = {}
        image_paths = self.inputs["image_paths"].data
        n_series = len(list(image_paths))
        self.event_manager.notify(ProgressEvent(percent=0, process=f"Spot detection: Starting"))
        for iN, image_id in enumerate(list(image_paths)):
            if self.user_segmentation_channel in image_paths[image_id] and os.path.isfile(self.inputs["image_paths"].data[image_id][self.user_segmentation_channel]):
                image_path = self.inputs["image_paths"].data[image_id][self.user_segmentation_channel]
                directory, filename = os.path.split(image_path)
                name, _ = os.path.splitext(filename)
                new_filename = f"{name}{self.user_mask_suffix}.npy"
                new_path = os.path.join(directory, new_filename)
                mask_paths[image_id] = {}
                mask_paths[image_id][self.user_segmentation_channel] = new_path
                image = tifffile.imread(image_path) #X,Y,Z
                if image.ndim == 3:
                    rna = np.transpose(image, (2,1,0)) #Z,Y,X for big-fish
                else:
                    rna = np.transpose(image, (1,0)) #Y,X for big-fish
                try:
                    spots, threshold = detect_spots(rna, remove_duplicate=self.user_remove_duplicate, threshold=None if not self.user_use_threshold else self.user_threshold, return_threshold=True,
                                                              voxel_size=(self.user_voxel_size_y_nm, self.user_voxel_size_x_nm) if image.ndim == 2 else (self.user_voxel_size_z_nm, self.user_voxel_size_y_nm, self.user_voxel_size_x_nm), spot_radius=(self.user_spot_radius_y_nm, self.user_spot_radius_x_nm) if image.ndim == 2 else (self.user_spot_radius_z_nm, self.user_spot_radius_y_nm, self.user_spot_radius_x_nm), log_kernel_size=None if not self.user_use_log_kernel_and_minimum_distance else (self.user_log_kernel_y_pixels, self.user_log_kernel_x_pixels) if image.ndim == 2 else (self.user_log_kernel_z_pixels, self.user_log_kernel_y_pixels, self.user_log_kernel_x_pixels),
                                                              minimum_distance=None if not self.user_use_log_kernel_and_minimum_distance else (self.user_minimum_distance_y_pixels, self.user_minimum_distance_x_pixels) if image.ndim == 2 else (self.user_minimum_distance_z_pixels, self.user_minimum_distance_y_pixels, self.user_minimum_distance_x_pixels))
                except Exception as e:
                    raise PipelineRunningException("Spot Detection Error",str(e))

                if image.ndim == 2:
                    empty_mask = {
                        "masks": np.zeros(image.shape, dtype=np.uint32),
                        "outlines": np.zeros(image.shape, dtype=np.uint32)
                    }
                else:
                    mask_shape = np.transpose(image, (2, 0, 1)).shape #Z,X,Y for cellpose masks
                    empty_mask = {
                        "masks": np.zeros(mask_shape, dtype=np.uint32),
                        "outlines": np.zeros(mask_shape, dtype=np.uint32)
                    }

                mask_seg = None
                if self.inputs["mask_paths"].data is not None:
                    if image_id in self.inputs["mask_paths"].data and self.user_segmentation_channel in self.inputs["mask_paths"].data[image_id]:
                        mask_seg = np.load(Path(self.inputs["mask_paths"].data[image_id][self.user_segmentation_channel]),allow_pickle=True).item()
                mask = create_spot_mask(spots, empty_mask,mask_seg, self.user_mask_spot_radius_pixels)
                np.save(new_path, mask)

                self.event_manager.notify(ProgressEvent(percent=int((iN + 1) / n_series * 100),
                                                        process=f"Spot detection images: {iN + 1}/{n_series}"))

        self.outputs["mask_paths"].data = mask_paths
        self.event_manager.notify(ProgressEvent(percent=100, process=f"Spot detection: Finished"))


def create_spot_mask(spots:list, mask:dict,mask_seg:dict, radius:float, thickness:int=1):
    """
    Create a mask and outline for a list of spots.
    (3d spot input in (Z,Y,X) => 3d mask output in (Z,X,Y))
    Arguments:
        spots (list): List of spot coordinates. For 2D images: [(y, x), ...], for 3D images: [(z, y, x), ...].
        mask (dict): Dictionary with two numpy arrays:
                        - "masks": integer array for the spots.
                        - "outlines": integer array for spots outlines.
        mask_seg (dict): Dictionary with two numpy arrays:
                        - "masks": integer array for segmented cells.
                        - "outlines": integer array for segmented cells outlines.
        radius (float): Radius of each spot in pixels/voxels.
        thickness (int, optional (default=1)): Thickness of the outline in pixels/voxels.
    Returns:
        mask (dict): Dictionary with two numpy arrays:
                        - "masks": integer array for the spots.
                        - "outlines": integer array for spots outlines.
    """
    bool_3d = mask["masks"].ndim == 3
    masks = mask["masks"]
    masks_seg = mask_seg["masks"] if mask_seg is not None else None
    if not np.any(masks_seg):
        masks_seg = None
    outlines = mask["outlines"]

    for i, coordinates in enumerate(spots):
        spot_id = i + 1

        if not bool_3d:
            y, x = coordinates
            y, x = int(round(y)), int(round(x))
            h, w = masks.shape #Z,X,Y

            x_min = int(max(x - radius - thickness, 0))
            x_max = int(min(x + radius + thickness + 1, w))#end is exclusive
            y_min = int(max(y - radius - thickness, 0))
            y_max = int(min(y + radius + thickness + 1, h))#end is exclusive

            x_grid,y_grid  = np.ogrid[x_min:x_max,y_min:y_max]
            eu_dist = np.sqrt((x_grid - x) ** 2 + (y_grid - y) ** 2) #Euclidean distance

            #bb is bounding_box
            bb_masks = masks[x_min:x_max, y_min:y_max]
            bb_masks_seg = masks_seg[x_min:x_max, y_min:y_max] if masks_seg is not None else None
            bb_outlines = outlines[x_min:x_max, y_min:y_max]

            if bb_masks_seg is not None:
                bb_masks[(eu_dist <= radius) & (bb_masks_seg != 0)] = spot_id
                bin_mask = (bb_masks == spot_id)
                outline_mask = binary_dilation(bin_mask,iterations=thickness) & (~bin_mask)
                bb_outlines[outline_mask] = spot_id
            else:
                bb_masks[eu_dist <= radius] = spot_id
                bin_mask = (bb_masks == spot_id)
                outline_mask = binary_dilation(bin_mask,iterations=thickness) & (~bin_mask)
                bb_outlines[outline_mask] = spot_id
        else:
            z, y, x = coordinates
            z, y, x = int(round(z)), int(round(y)), int(round(x))
            d, h, w = masks.shape #Z,X,Y

            z_min = int(max(z - radius - thickness, 0))
            z_max = int(min(z + radius + thickness + 1, d))#end is exclusive
            x_min = int(max(x - radius - thickness, 0))
            x_max = int(min(x + radius + thickness + 1, w))#end is exclusive
            y_min = int(max(y - radius - thickness, 0))
            y_max = int(min(y + radius + thickness + 1, h))#end is exclusive

            z_grid, x_grid, y_grid  = np.ogrid[z_min:z_max,x_min:x_max,y_min:y_max]
            eu_dist = np.sqrt((z_grid - z) ** 2 + (x_grid - x) ** 2 + (y_grid - y) ** 2) #Euclidean distance

            #bb is bounding box
            bb_masks = masks[z_min:z_max, x_min:x_max, y_min:y_max]
            bb_masks_seg = masks_seg[z_min:z_max, x_min:x_max, y_min:y_max] if masks_seg is not None else None
            bb_outlines = outlines[z_min:z_max, x_min:x_max, y_min:y_max]

            if bb_masks_seg is not None:
                bb_masks[(eu_dist <= radius) & (bb_masks_seg != 0)] = spot_id
                bin_mask = (bb_masks == spot_id)
                outline_mask = binary_dilation(bin_mask,iterations=thickness) & (~bin_mask)
                bb_outlines[outline_mask] = spot_id
            else:
                bb_masks[eu_dist <= radius] = spot_id
                bin_mask = (bb_masks == spot_id)
                outline_mask = binary_dilation(bin_mask,iterations=thickness) & (~bin_mask)
                bb_outlines[outline_mask] = spot_id

    return mask

