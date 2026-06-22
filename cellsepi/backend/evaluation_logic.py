import pickle
import traceback
import json
import os

def run_cellpose_evaluation(image_paths, mask_paths, model_path, model_type_str,
                            segmentation_channel, diameter, suffix, gpu_flag,
                            delete_small_masks, mask_deletion_diameter, rescale_settings):
    import numpy as np
    import cv2
    import torch
    from tifffile import tifffile
    from cellpose import models, io
    from backend.CellposeV3 import modelsV3, ioV3
    from backend.constants import ModelType
    from backend.settings import SegmentationConfig
    from backend.image_utils import normalize_image, rescale_image
                              
    try:
        if isinstance(rescale_settings, dict):
            rescale_settings = SegmentationConfig(**rescale_settings)
        model_type = next((m for m in ModelType if m.value.name == model_type_str), None)
        if model_type is None:
            print(json.dumps({"type": "error", "text": f"Model type {model_type_str} not supported!"}), flush=True)
            return

        device = torch.device("cuda" if torch.cuda.is_available() and gpu_flag else (
            "mps" if torch.mps.is_available() and gpu_flag else "cpu"))

        print(json.dumps({"type": "log", "text": ">>> Loading Model..."}), flush=True)

        if model_type == ModelType.CUSTOM:
            state_dict = torch.load(model_path, map_location=device, weights_only=True)
            w2_data = state_dict.get('W2', None)
            if w2_data is None:
                model = modelsV3.CellposeModel(pretrained_model=model_path, gpu=gpu_flag)
                model_type = ModelType.CP_CYTO
            else:
                model = models.CellposeModel(pretrained_model=model_path, gpu=gpu_flag)
                model_type = ModelType.CP_SAM
        elif model_type == ModelType.CP_CYTO:
            model = modelsV3.CellposeModel(model_type="cyto3", gpu=gpu_flag)
        elif model_type == ModelType.CP_NUCLEI:
            model = modelsV3.CellposeModel(model_type="nuclei", gpu=gpu_flag)
        elif model_type == ModelType.CP_SAM:
            model = models.CellposeModel(gpu=gpu_flag)

        n_images = len(image_paths)
        print(json.dumps({"type": "log", "text": f">>> Starting Evaluation of {n_images} images..."}), flush=True)

        current_done_count = sum(
            1 for img_id in mask_paths
            if segmentation_channel in mask_paths[img_id] and mask_paths[img_id][segmentation_channel] is not None
        )
        for iN, image_id in enumerate(image_paths):
            current_diameter = diameter

            if image_id in mask_paths and segmentation_channel in mask_paths[image_id] and mask_paths[image_id][
                segmentation_channel] is not None:
                percent = int((current_done_count / n_images) * 100)
                print(json.dumps({"type": "progress", "percent": percent, "image_id": image_id, "skipped": True}),
                      flush=True)
                continue

            image_path = image_paths[image_id][segmentation_channel]
            image = tifffile.imread(image_path)
            original_shape = image.shape
            original_image = image.copy()

            image = image.astype(np.float32)
            image = normalize_image(image)
            image = rescale_image(image, rescale_settings=rescale_settings)
            factor = np.max(image.shape[-2:]) / np.max(original_shape[-2:])
            current_diameter = current_diameter * factor

            if model_type in [ModelType.CP_NUCLEI, ModelType.CP_CYTO]:
                if image.ndim == 3:
                    res = model.eval(image, diameter=current_diameter, channels=[0, 0], z_axis=0, do_3D=False,
                                     stitch_threshold=0.5)
                else:
                    res = model.eval(image, diameter=current_diameter, channels=[0, 0])
                mask, flow, style = res[:3]

            elif model_type == ModelType.CP_SAM:
                if image.ndim == 3:
                    res = model.eval(image, diameter=current_diameter, z_axis=0, do_3D=False, stitch_threshold=0.5)
                else:
                    res = model.eval(image, diameter=current_diameter)
                mask, flow, style = res[:3]

            if mask is not None:
                mask = rescale_image(mask, target_shape=original_shape, interpolation=cv2.INTER_NEAREST)

            if flow is not None:
                fraction_y = original_shape[-2] / flow[0].shape[-3]
                fraction_x = original_shape[-1] / flow[0].shape[-2]

                flow[0] = np.stack(
                    [rescale_image(flow[0][..., iD], target_shape=original_shape)
                     for iD in range(flow[0].shape[-1])],
                    axis=-1
                )

                flow[1] = np.stack(
                    [rescale_image(flow[1][z], target_shape=original_shape)
                     for z in range(flow[1].shape[0])],
                    axis=0
                )
                flow[1][-2] = flow[1][-2] * fraction_y
                flow[1][-1] = flow[1][-1] * fraction_x

                flow[2] = rescale_image(
                    flow[2],
                    target_shape=original_shape,
                    interpolation=cv2.INTER_NEAREST
                )

            if delete_small_masks and mask is not None:
                threshold = mask_deletion_diameter
                counts = np.bincount(mask.ravel())
                for cell_id, size in enumerate(counts[1:], start=1):
                    if size == 0: continue
                    diam = 2 * ((3 * size) / (4 * np.pi)) ** (1 / 3) if mask.ndim == 3 else 2 * np.sqrt(size / np.pi)
                    if diam < threshold:
                        mask[mask == cell_id] = 0

            directory, filename = os.path.split(image_path)
            name, _ = os.path.splitext(filename)
            new_path = os.path.join(directory, f"{name}{suffix}.npy")

            if model_type in [ModelType.CP_NUCLEI, ModelType.CP_CYTO]:
                ioV3.masks_flows_to_seg([original_image], [mask], [flow], [image_path])
            elif model_type == ModelType.CP_SAM:
                io.masks_flows_to_seg([original_image], [mask], [flow], [image_path])

            default_suffix_path = os.path.splitext(image_path)[0] + '_seg.npy'
            if default_suffix_path != new_path:
                if os.path.exists(default_suffix_path):
                    if os.path.exists(new_path): os.remove(new_path)
                    os.rename(default_suffix_path, new_path)

            current_done_count += 1
            percent = round((current_done_count / n_images) * 100)
            print(json.dumps(
                {"type": "progress", "percent": percent, "image_id": image_id, "new_path": new_path, "skipped": False}),
                  flush=True)

        print(json.dumps({"type": "finished", "text": "Evaluation Complete"}), flush=True)



    except pickle.UnpicklingError as ex:
        print(json.dumps({
            "type": "error",
            "error_trace": traceback.format_exc(),
            "error_type": "UnpicklingError"
        }), flush=True)

    except Exception:
        print(json.dumps({
            "type": "error",
            "error_trace": traceback.format_exc(),
            "error_type": "Generic"
        }), flush=True)
