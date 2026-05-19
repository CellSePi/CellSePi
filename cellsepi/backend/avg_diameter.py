from concurrent.futures import ThreadPoolExecutor
import numpy as np


def calculate_mask_diameters(mask):
    """
    Calculates the diameter of each cell in the given mask by assuming circular cells.

    Attributes:
        mask: the mask of an image
    Returns:
        list[]: the diameter of each cell in the given mask
    """
    cell_ids = np.unique(mask)
    diameters = []
    cell_ids = cell_ids[1:]

    for cell_id in cell_ids:
        cell_mask = mask == cell_id
        cell_area = np.sum(cell_mask)

        # Approximate diameter assuming circular cells
        cell_diameter = 2 * np.sqrt(cell_area / np.pi)
        diameters.append(cell_diameter)

    return diameters

class AverageDiameter:
    """
    This class calculates the average diameter of a cell in all the given images.
    """
    def __init__(self, gui):
        self.gui = gui
        self.csp = gui.csp

    def get_avg_diameter(self):
        """
        This method calculates the average diameter of a cell in all the given images.
        Returns: The average diameter of all cells rounded to 2 decimal places.
        """
        mask_paths = self.csp.mask_paths
        if mask_paths is not None:
            segmentation_channel = self.csp.config.get_bf_channel()
            all_diameters = []
            valid_image_id = [
                key for key in mask_paths.keys()
                if isinstance(mask_paths[key], dict) and segmentation_channel in mask_paths[key]
            ]

            def process_image(image_id):
                mask_path = mask_paths[image_id][segmentation_channel]
                mask_data = np.load(mask_path, allow_pickle=True).item()
                mask = mask_data["masks"]
                return calculate_mask_diameters(mask)
            try:
                with ThreadPoolExecutor() as executor:
                    results = executor.map(process_image, valid_image_id)

                for diameters in results:
                    all_diameters.extend(diameters)

                if len(all_diameters) == 0:
                    return 0.00

                rounded_diameters = round(np.mean(all_diameters), 2)
                self.gui.training_environment.diameter = rounded_diameters
                if self.gui.training_environment.field_diameter.disabled is False:
                    self.gui.training_environment.field_diameter.value = rounded_diameters
                    self.gui.training_environment.field_diameter.update()
                return rounded_diameters
            except:
                return self.gui.diameter_text.value


