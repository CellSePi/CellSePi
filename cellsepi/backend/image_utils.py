import cv2
import numpy as np
from backend.settings import SettingsManager, DownscaleMode


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


def rescale_image(image, target_shape=None, rescale_settings=None):
    if target_shape is None and rescale_settings is None:
        raise ValueError("Either target_shape or rescale_settings must be provided.")

    if target_shape is None:
        match rescale_settings.mode:
            case DownscaleMode.NONE:
                target_shape = image.shape
            case DownscaleMode.PIXELS:
                max_pixels = int(rescale_settings.max_pixels)
                max_size = np.max(image.shape[-2:])
                fraction = max_pixels / max_size
                target_shape = tuple((fraction * np.array(image.shape)).astype(int))
            case DownscaleMode.FRACTION:
                fraction = float(rescale_settings.max_fraction)
                target_shape = tuple((fraction * np.array(image.shape)).astype(int))

    if np.max(target_shape) > np.max(image.shape):
        # Upscaling
        interpolation = cv2.INTER_CUBIC
    else:
        # Downscaling
        interpolation = cv2.INTER_AREA

    image = cv2.resize(image, target_shape, interpolation=interpolation)

    return image
