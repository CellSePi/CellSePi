import cv2
import numpy as np

from image_editing_view import normalize_image as fast_normalize_image
from backend.settings import SettingsManager, DownscaleMode


def normalize_image(image: np.ndarray, ) -> np.ndarray:
    """
    image: np.ndarray of type float with format Z, Y, X or Y, X
    returns: np.ndarray of type float normalized between 0 and 1
    """
    settings = SettingsManager().settings.image

    return fast_normalize_image(
        image,
        margin=settings.margin,
        lower_quantile=settings.lower_quantile,
        upper_quantile=settings.upper_quantile
    )


def rescale_image(image, target_shape=None, rescale_settings=None, interpolation=None):
    if target_shape is None and rescale_settings is None:
        raise ValueError("Either target_shape or rescale_settings must be provided.")
    is_3d = image.ndim == 3
    if target_shape is None:
        spatial_shape = np.array(image.shape[-2:])
        match rescale_settings.mode:
            case DownscaleMode.NONE:
                target_shape = image.shape
            case DownscaleMode.PIXELS:
                max_pixels = int(rescale_settings.max_pixels)
                max_size = np.max(spatial_shape)
                fraction = max_pixels / max_size
                target_spatial = tuple((fraction * spatial_shape).astype(int))
                target_shape = (image.shape[0], *target_spatial) if is_3d else target_spatial

            case DownscaleMode.FRACTION:
                fraction = float(rescale_settings.max_fraction)
                target_spatial = tuple((fraction * spatial_shape).astype(int))
                target_shape = (image.shape[0], *target_spatial) if is_3d else target_spatial
    if interpolation is None:
        if np.max(target_shape[-2:]) > np.max(image.shape[-2:]):
            # Upscaling
            interpolation = cv2.INTER_CUBIC
        else:
            # Downscaling
            interpolation = cv2.INTER_AREA

    dsize = (target_shape[-1], target_shape[-2])
    if image.ndim == 3:
        rescaled_slices = []
        for z in range(image.shape[0]):
            slice_2d = image[z]
            resized_slice = cv2.resize(slice_2d, dsize, interpolation=interpolation)
            rescaled_slices.append(resized_slice)
        image = np.stack(rescaled_slices, axis=0)
    else:
        image = cv2.resize(image, dsize, interpolation=interpolation)

    return image
