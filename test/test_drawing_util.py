import numpy as np

from drawing_util import mask_shifting
import pytest

mask_data = {
        "masks": np.array([
            [0, 1, 2, 3],
            [4, 5, 0, 6],
            [7, 0, 0, 8]
        ]),
        "outlines": np.array([
            [0, 1, 0, 2],
            [3, 0, 4, 5],
            [6, 0, 7, 8]
        ])
    }
mask = mask_data["masks"]
outline = mask_data["outlines"]

def test_drawing_util():

    mask_data_after_delete = {
        "masks": np.array([
            [0, 1, 2, 3],
            [4, 0, 0, 5],
            [6, 0, 0, 7]
        ]),
        "outlines": np.array([
            [0, 1, 0, 2],
            [3, 0, 4, 0],
            [5, 0, 6, 7]
        ])
    }
    cell_id = 5
    cell_mask = (mask == cell_id).copy()
    cell_outline = (outline == cell_id).copy()
    mask[cell_mask] = 0
    outline[cell_outline] = 0
    mask_shifting(mask_data,cell_id)
    assert np.array_equal(mask_data["masks"], mask_data_after_delete["masks"]), "Mask shifting failed for 'masks'"
    assert np.array_equal(mask_data["outlines"],mask_data_after_delete["outlines"]), "Mask shifting failed for 'outlines'"

def test_drawing_util_invalid():
    cell_id = 0
    cell_mask = (mask == cell_id).copy()
    cell_outline = (outline == cell_id).copy()
    mask[cell_mask] = 0
    outline[cell_outline] = 0
    with pytest.raises(ValueError):
        mask_shifting(mask_data,cell_id)

