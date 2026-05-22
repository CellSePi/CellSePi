import numpy as np
from backend.settings import SettingsManager


def normalize_image(image: np.ndarray, ) -> np.ndarray:
    """
    image: np.ndarray of type float with format Z, Y, X or Y, X
    returns: np.ndarray of type float normalized between 0 and 1
    """
    settings = SettingsManager().settings.image

    shape = np.array(image.shape)

    offset = shape * settings.margin
    offset = offset.astype(int)

    cropped_image = image[..., offset[-2]: -offset[-2], offset[-1]: -offset[-1]]

    min_val = np.quantile(cropped_image, settings.lower_quantile)
    max_val = np.quantile(cropped_image, settings.upper_quantile)
    if (max_val - min_val) > 0:
        image = (image - min_val) / (max_val - min_val)
    else:
        image = np.zeros_like(image)

    image[image < 0] = 0
    image[image > 1] = 1
    return image
