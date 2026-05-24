import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor

SHARED_EXECUTOR = ThreadPoolExecutor(max_workers=2)


def calculate_mask_diameters(mask):
    diameters = []

    if mask.ndim == 3:
        for z in range(mask.shape[0]):
            slice_mask = mask[z]
            if np.any(slice_mask):
                counts = np.bincount(slice_mask.ravel())
                areas = counts[1:]
                valid_areas = areas[areas > 0]
                diameters.extend((2 * np.sqrt(valid_areas / np.pi)).tolist())
    else:
        counts = np.bincount(mask.ravel())
        areas = counts[1:]
        valid_areas = areas[areas > 0]
        diameters = (2 * np.sqrt(valid_areas / np.pi)).tolist()

    return diameters


class AverageDiameter:
    def __init__(self, gui):
        self.gui = gui
        self.csp = gui.csp
        self._diameter_cache = {}

    def _process_image(self, args):
        image_id, segmentation_channel = args
        mask_path = self.csp.mask_paths[image_id][segmentation_channel]

        try:
            if not os.path.exists(mask_path):
                return (image_id, segmentation_channel), []

            mask_data = np.load(mask_path, allow_pickle=True).item()
            mask = mask_data["masks"]
            return (image_id, segmentation_channel), calculate_mask_diameters(mask)

        except:
            return (image_id, segmentation_channel), []

    def clear_cache(self):
        self._diameter_cache.clear()

    def remove_image_from_cache(self, image_id):
        current_seg_channel = self.csp.config.get_bf_channel()
        cache_key = (image_id, current_seg_channel)

        self._diameter_cache.pop(cache_key, None)

    async def get_avg_diameter(self, update_image_id=None):
        mask_paths = self.csp.mask_paths
        if not mask_paths:
            return 0.00


        current_seg_channel = self.csp.config.get_bf_channel()

        valid_image_ids = [
            key for key in mask_paths.keys()
            if isinstance(mask_paths[key], dict) and current_seg_channel in mask_paths[key]
        ]

        try:
            if update_image_id is not None:
                cache_key = (update_image_id, current_seg_channel)
                _, new_diameters = self._process_image(cache_key)
                self._diameter_cache[cache_key] = new_diameters

            else:
                missing_args = [
                    (img_id, current_seg_channel) for img_id in valid_image_ids
                    if (img_id, current_seg_channel) not in self._diameter_cache
                ]

                if missing_args:
                    results = SHARED_EXECUTOR.map(self._process_image, missing_args)
                    for cache_key, diams in results:
                        self._diameter_cache[cache_key] = diams

            all_diameters = []
            for img_id in valid_image_ids:
                key = (img_id, current_seg_channel)
                if key in self._diameter_cache:
                    all_diameters.extend(self._diameter_cache[key])

            if len(all_diameters) == 0:
                rounded_diameters = 0.00
            else:
                rounded_diameters = round(np.mean(all_diameters), 2)

            self.gui.training_environment.diameter = rounded_diameters
            if self.gui.training_environment.field_diameter.disabled is False:
                self.gui.training_environment.field_diameter.value = str(rounded_diameters)
                self.gui.training_environment.field_diameter.update()

            self.gui.diameter_text.value = str(rounded_diameters)
            self.gui.diameter_text.update()

        except:
            return