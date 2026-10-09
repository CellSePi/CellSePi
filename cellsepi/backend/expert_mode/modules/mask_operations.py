import os
import pathlib
from enum import auto

import numpy as np
from tifffile import tifffile

from backend.expert_mode.listener import ProgressEvent
from backend.expert_mode.module import *
from backend.expert_mode.pipeline_manager import PipelineRunningException


class MaskOperation(Enum):
    DIFFERENCE = auto()  # Substract all masks in B from each mask in A
    UNION = auto()  # Join all masks and give individual ids
    INTERSECTION = auto()  # Only keep those masks in A that lie in a mask of B


class MaskOperations(Module):
    _gui_config = ModuleGuiConfig(
        "MaskOperations",
        Categories.FILTERS,
        "This module provides set operations on masks featuring the same dimensions.")

    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.inputs = InputPorts(
            InputPort("mask_paths", dict, multi=["A", "B"]),
        )
        self.outputs = OutputPorts(
            InputPort("mask_paths", dict),
        )
        self.user_operation: MaskOperation = MaskOperation.DIFFERENCE
        self.user_Mask_Channel_A: int = 1
        self.user_Mask_Channel_B: int = 2

    def run(self):
        base_dir = self.get_working_directory()

        # ToDo Continue here with checking how values for A and B can be ob
        masks_A = self.inputs.mask_paths.data["A"][-1]
        masks_B = self.inputs.mask_paths.data["B"][-1]
        n_series = len(masks_A)
        n_series_B = len(masks_B)
        assert n_series == n_series_B, "Number of series in A and B must be equal."

        channel_A = str(self.user_Mask_Channel_A)
        channel_B = str(self.user_Mask_Channel_B)

        self.event_manager.notify(ProgressEvent(percent=0, process=f"Mask Operations: Starting"))

        outputs_masks = {}

        for iN, series in enumerate(masks_A):
            if self.is_cancelled():
                self.outputs.mask_paths.data = outputs_masks
                self.event_manager.notify(
                    ProgressEvent(percent=int((iN) / n_series * 100), process="Mask Opterations: Cancelled")
                )
                return
            outputs_masks[series] = {}

            assert series in masks_B, f"Series {series} not found in B."


            assert channel_A in masks_A[series], f"Channel {channel_A} not found in A series {series}."
            assert channel_B in masks_B[series], f"Channel {channel_B} not found in B series {series}."

            mask_A_path = masks_A[series][channel_A]
            mask_A_path = pathlib.Path(mask_A_path)

            mask_A = np.load(mask_A_path, allow_pickle=True).item()
            # mask_A = mask_A_data["masks"].astype(np.uint16)


            mask_B_path = masks_B[series][channel_B]
            mask_B_path = pathlib.Path(mask_B_path)

            mask_B = np.load(mask_B_path, allow_pickle=True).item()
            # mask_B = mask_B_data["masks"].astype(np.uint16)

            if self.user_operation == MaskOperation.DIFFERENCE:
                suffix = "_diff"
                new_mask = substract_masks(mask_A, mask_B)

            elif self.user_operation == MaskOperation.UNION:
                suffix = "_union"
                new_mask = unite_masks(mask_A, mask_B)

            elif self.user_operation == MaskOperation.INTERSECTION:
                suffix = "_intersection"
                new_mask = intersect_masks(mask_A, mask_B)

            else:
                raise PipelineRunningException("Value Error", "Invalid mask operation.")

            name_without_type = mask_A_path.stem

            new_filename = f"{name_without_type}{suffix}.npy"
            new_path = os.path.join(base_dir, new_filename)

            np.save(new_path, new_mask)

            outputs_masks[series][channel_A] = new_path

            self.event_manager.notify(
                ProgressEvent(
                    percent=int((iN + 1) / n_series * 100),
                    process=f"Projecting Series: {iN + 1}/{n_series}"
                )
            )
        self.outputs.mask_paths.data = outputs_masks
        self.event_manager.notify(ProgressEvent(percent=100, process=f"Mask Operations: Finished"))


def substract_masks(mask_A, mask_B):
    new_mask = dict(mask_A)

    new_mask_mask = np.array(new_mask["masks"]).astype(np.uint16)
    outlines = np.array(new_mask["outlines"])

    mask_B_mask = mask_B["masks"].astype(np.uint16)
    mask_B_derif = np.array(mask_B_mask).astype(np.float32)
    mask_B_derif[mask_B_derif > 0] = np.nan

    new_mask_mask = new_mask_mask - mask_B_derif
    new_mask_mask[np.isnan(new_mask_mask)] = 0
    new_mask_mask = new_mask_mask.astype(np.uint16)

    new_outlines = outlines - mask_B_derif
    new_outlines[np.isnan(new_outlines)] = 0
    new_outlines = new_outlines.astype(np.uint16)

    new_mask["masks"] = new_mask_mask
    new_mask["outlines"] = new_outlines

    # ToDo Flows aren't handled yet

    return new_mask


def unite_masks(mask_A, mask_B):
    new_mask = dict(mask_A)

    mask_A_mask = np.array(new_mask["masks"]).astype(np.uint16)
    mask_A_outlines = np.array(new_mask["outlines"]).astype(np.uint16)

    # Necessary to prevent overlapping masks
    mask_B_diff = substract_masks(mask_B, mask_A)

    mask_B_mask = np.array(mask_B_diff["masks"]).astype(np.uint16)
    mask_B_outlines = np.array(mask_B_diff["outlines"]).astype(np.uint16)

    offset = np.max(mask_A_mask)
    mask_B_mask[mask_B_mask > 0] = offset + mask_B_mask[mask_B_mask > 0]
    mask_B_outlines[mask_B_outlines > 0] = offset + mask_B_outlines[mask_B_outlines > 0]

    new_mask_mask = mask_A_mask + mask_B_mask
    new_outlines = mask_A_outlines + mask_B_outlines

    new_mask["masks"] = new_mask_mask
    new_mask["outlines"] = new_outlines

    # ToDo Flows aren't handled yet

    return new_mask


def intersect_masks(mask_A, mask_B):
    new_mask = dict(mask_A)

    mask_A_mask = np.array(new_mask["masks"]).astype(np.uint16)
    mask_A_outlines = np.array(new_mask["outlines"]).astype(np.uint16)

    mask_B_mask = np.array(mask_B["masks"]).astype(np.uint16)
    # mask_B_outlines = np.array(mask_B["outlines"]).astype(np.uint16)

    mask_A_mask[mask_B_mask == 0] = 0
    mask_A_outlines[mask_B_mask == 0] = 0

    new_mask_mask = mask_A_mask
    new_outlines = mask_A_outlines

    new_mask["masks"] = new_mask_mask
    new_mask["outlines"] = new_outlines

    # ToDo Flows aren't handled yet

    return new_mask
