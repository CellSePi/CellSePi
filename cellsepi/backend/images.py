import cv2
import os
import pathlib
import shutil
import threading

import pandas as pd

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion
from tifffile import tifffile

from backend.constants import ExportFileType, ModelType
from backend.data_util import load_image_to_numpy, export_dataframe_to_pdf
from backend.expert_mode.event_manager import EventManager
from backend.expert_mode.listener import ProgressEvent
from backend.notifier import Notifier

from backend.image_utils import normalize_image, rescale_image
from backend.settings import SettingsManager, DownscaleMode


class BatchImageSegmentation(Notifier):
    """
    This class handles the segmentation of the images.
    """
    GPU: bool = False

    def __init__(self,
                 segmentation=None,
                 gui=None,
                 segmentation_channel: str = "",
                 diameter: float = 125.0,
                 suffix: str = "_seg"):
        if gui is not None:
            super().__init__()
            self.segmentation = segmentation
            self.gui = gui
            self.segmentation_channel = self.gui.csp.config.get_bf_channel()
            self.diameter = self.gui.csp.config.get_diameter()
            self.suffix = self.gui.csp.current_mask_suffix
        else:
            self.segmentation_channel = segmentation_channel
            self.diameter = diameter
            self.suffix = suffix

        self.masks_backup = {}
        self.prev_masks_exist = False
        self.num_seg_images = 0
        self.cancel_now = False
        self.pause_now = False
        self.resume_now = False
        self.executor = None
        self.progress_lock = threading.Lock()
        self.progress = 0

    def _is_cancelled(self, cancel_event=None) -> bool:
        """
        Checks both cancel sources: the legacy GUI flag (cancel_now) and an
        optionally injected threading.Event from a pipeline module.
        """
        if self.cancel_now:
            return True
        if cancel_event is not None and cancel_event.is_set():
            return True
        return False

    def get_contour_from_labeled_mask(label_mask):
        outlines = np.zeros_like(label_mask, dtype=np.uint16)
        obj_ids = np.unique(label_mask)
        obj_ids = obj_ids[obj_ids != 0]

        for obj_id in obj_ids:
            mask = label_mask == obj_id
            eroded = binary_erosion(mask)
            outline = mask & (~eroded)
            outlines[outline] = 255

        return outlines

    def masks_to_label_mask(self, masks):
        N, H, W = masks.shape
        label_mask = np.zeros((H, W), dtype=np.int32)

        for i in range(N):
            mask = masks[i].astype(bool)
            label_mask[mask] = i + 1

        return label_mask

    def delete_mask(self, path, channels_to_delete, image_id, segmentation_channel):
        if os.path.exists(path):
            channels_to_delete.append((image_id, segmentation_channel))
            if image_id == self.gui.csp.image_id:
                if self.segmentation_channel == segmentation_channel:
                    self.gui.canvas.reset_mask()
                    return
            os.remove(path)

    # the following methods handle the different actions and handle accordingly
    def cancel_action(self):
        self.cancel_now = True
        if self.executor is not None:
            self.executor.shutdown(wait=True)

    def pause_action(self):
        self.pause_now = True
        if self.executor is not None:
            self.executor.shutdown(wait=True)

    def resume_action(self):
        self.resume_now = True

    def run(self, event_manager: EventManager = None, image_paths=None, mask_paths=None, model_path=None,
            model_type=None,cancel_event=None):
        """
        Applies the segmentation model to every image and stores the resulting masks.
        """
        import torch
        import torchvision.transforms as T
        from cellpose import models, io
        from backend.CellposeV3 import modelsV3, ioV3
        if event_manager is None:
            print("event_manager is None")
            if self.num_seg_images == 0:  # shouldn't backup again, if it was paused and now resuming
                self.segmentation_channel = self.gui.csp.config.get_bf_channel()
                self.diameter = self.gui.csp.config.get_diameter()
                self.suffix = self.gui.csp.current_mask_suffix
        if self._is_cancelled(cancel_event):
            self.cancel_now = False
            self.num_seg_images = 0
            return
        elif event_manager is None and self.pause_now:
            self.pause_now = False
            return
        elif event_manager is None and self.resume_now:
            self.resume_now = False
            self.segmentation.is_resuming()

        if event_manager is None:
            self._call_start_listeners()
        if event_manager is None:
            image_paths = self.gui.csp.image_paths
            mask_paths = self.gui.csp.mask_paths

        segmentation_channel = self.segmentation_channel
        suffix = self.suffix

        n_images = len(image_paths)

        if event_manager is None:
            segmentation_model = self.gui.csp.model_path
        else:
            segmentation_model = model_path
            event_manager.notify(ProgressEvent(0, f"Segmenting Images: 0/{n_images}"))

        if self.GPU:
            device = torch.device(
                "cuda" if torch.cuda.is_available() else ("mps" if torch.mps.is_available() else "cpu"))
        else:
            device = torch.device("cpu")

        if event_manager is None:
            model_type = self.gui.csp.model_type

        if model_type == ModelType.CUSTOM:
            state_dict = torch.load(segmentation_model, map_location=device, weights_only=True)
            w2_data = state_dict.get('W2', None)
            if w2_data is None:
                model = modelsV3.CellposeModel(pretrained_model=segmentation_model, gpu=self.GPU)
                ioV3.logger_setup()
                model_type = ModelType.CP_CYTO
            else:
                model = models.CellposeModel(pretrained_model=segmentation_model, gpu=self.GPU)
                io.logger_setup()
                model_type = ModelType.CP_SAM
        elif model_type == ModelType.CP_CYTO:
            model = modelsV3.CellposeModel(model_type="cyto3", gpu=self.GPU)
            ioV3.logger_setup()
        elif model_type == ModelType.CP_NUCLEI:
            model = modelsV3.CellposeModel(model_type="nuclei", gpu=self.GPU)
            ioV3.logger_setup()
        elif model_type == ModelType.CP_SAM:
            model = models.CellposeModel(gpu=self.GPU)
            io.logger_setup()

        """else:
            model_type = 'pytorch'
            model = maskrcnn_resnet50_fpn(weights="DEFAULT")
            in_features = model.roi_heads.box_predictor.cls_score.in_features
            model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes=2)
            in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
            model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, 256,num_classes=2)

            model.load_state_dict(torch.load(segmentation_model, map_location=self.device))
            model.to(self.device)
            model.eval()"""

        start_index = self.num_seg_images
        settings_manager = SettingsManager()
        for iN, image_id in enumerate(list(image_paths)[start_index:], start=start_index):
            diameter = self.diameter
            if (segmentation_channel in image_paths[image_id]
                    and os.path.isfile(image_paths[image_id][segmentation_channel])):
                if self._is_cancelled(cancel_event):
                    self.cancel_now = False
                    self.num_seg_images = 0
                    return
                elif event_manager is None and self.pause_now:
                    self.pause_now = False
                    return
                elif event_manager is None and self.resume_now:
                    self.resume_now = False
                    self.segmentation.is_resuming()

                if mask_paths and image_id in mask_paths and mask_paths[image_id] is not None and segmentation_channel in mask_paths[image_id]:
                    if mask_paths[image_id][segmentation_channel] is not None:
                        print("skip image, mask already exists")
                        percent = round((iN + 1) / n_images * 100)
                        progress = str(percent) + " %"
                        if event_manager is None:
                            current_image = {"image_id": image_id, "path": None}
                            self._call_update_listeners(progress, current_image)
                        else:
                            event_manager.notify(ProgressEvent(percent=percent,
                                                               process=f"Segmenting Images: {iN + 1}/{n_images} (Latest Image: {image_id})"))
                        self.num_seg_images = self.num_seg_images + 1
                        continue

                image_path = image_paths[image_id][segmentation_channel]
                image = tifffile.imread(image_path)

                original_shape = image.shape
                original_image = image.copy()
                # print(f"Original Shape: {original_shape}")

                # Normalization
                image = image.astype(np.float32)
                image = normalize_image(image)

                # Rescaling
                rescale_settings = settings_manager.settings.performance.segmentation_downscaling
                image = rescale_image(image, rescale_settings=rescale_settings)
                factor = np.max(image.shape[-2:]) / np.max(original_shape[-2:])
                diameter = diameter * factor
                # print(f"Rescaled Shape: {image.shape}")

                # model evaluates image
                if model_type == ModelType.CP_NUCLEI or model_type == ModelType.CP_CYTO:
                    if image.ndim == 3:  # z, y, x dimensions
                        res = model.eval(image, diameter=diameter, channels=[0, 0], z_axis=0, do_3D=False,
                                         stitch_threshold=0.5)
                    else:
                        res = model.eval(image, diameter=diameter, channels=[0, 0])
                    mask, flow, style = res[:3]

                elif model_type == ModelType.CP_SAM:
                    if image.ndim == 3:  # z, y, x dimensions
                        res = model.eval(image, diameter=diameter, z_axis=0, do_3D=False, stitch_threshold=0.5)
                    else:
                        res = model.eval(image, diameter=diameter)
                    mask, flow, style = res[:3]

                elif model_type == 'pytorch':
                    # PyTorch models expect tensor with shape [C, H, W], normalized
                    if image.ndim == 2:  # grayscale
                        image = np.stack([image] * 3, axis=-1)
                    elif image.shape[2] == 1:
                        image = np.concatenate([image] * 3, axis=-1)

                    pil_img = Image.fromarray((image * 65535).astype(np.uint16))
                    transform = T.ToTensor()
                    img_tensor = transform(pil_img).to(device)

                    with torch.no_grad():
                        prediction = model([img_tensor])[0]

                    if 'masks' not in prediction or len(prediction['masks']) == 0:
                        mask = np.zeros_like(image[..., 0], dtype=np.uint16)
                    else:
                        masks = prediction['masks'] > 0.5
                        mask = masks.squeeze(1).cpu().numpy()

                        mask = self.masks_to_label_mask(mask)

                    flow, style = None, None

                # print(f"Original Mask Shape: {mask.shape}")
                # Restore the original image shape and adapt the masks and flows accordingly
                if mask is not None:
                    mask = rescale_image(mask, target_shape=original_shape,interpolation=cv2.INTER_NEAREST)
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

                # delete small masks below user defined diameter
                if settings_manager.settings.segmentation.delete_small_masks and mask is not None:

                    threshold = settings_manager.settings.segmentation.mask_deletion_diameter

                    counts = np.bincount(mask.ravel())

                    for cell_id, size in enumerate(counts[1:], start=1):

                        if size == 0:
                            continue

                        if mask.ndim == 3:
                            # equivalent sphere diameter
                            diameter = 2 * ((3 * size) / (4 * np.pi)) ** (1 / 3)
                        else:
                            # equivalent circle diameter
                            diameter = 2 * np.sqrt(size / np.pi)
                        if diameter < threshold:
                            mask[mask == cell_id] = 0

                image = original_image

                # Generate the output filename directly using the suffix attribute
                directory, filename = os.path.split(image_path)
                name, _ = os.path.splitext(filename)
                new_filename = f"{name}{suffix}.npy"
                new_path = os.path.join(directory, new_filename)

                default_suffix_path = os.path.splitext(image_path)[0] + '_seg.npy'
                """
                backup_path = None
                if default_suffix_path != new_path:
                    if os.path.exists(default_suffix_path):
                        backup_path = default_suffix_path + '.backup'
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                        os.rename(default_suffix_path, backup_path)
                """
                # Save the segmentation results directly with the default name first
                if model_type == ModelType.CP_NUCLEI or model_type == ModelType.CP_CYTO:
                    ioV3.masks_flows_to_seg([image], [mask], [flow], [image_path])
                elif model_type == ModelType.CP_SAM:
                    io.masks_flows_to_seg([image], [mask], [flow], [image_path])
                else:
                    H, W = image.shape[:2]
                    flow0 = np.zeros((H, W, 3), dtype=np.uint16)
                    flow1 = np.zeros((2, H, W), dtype=np.float32)
                    flow2 = np.zeros((H, W), dtype=np.float32)
                    dummy_flow = [flow0, flow1, flow2]
                    io.masks_flows_to_seg([image], [mask], [dummy_flow], [image_path])

                if default_suffix_path != new_path:
                    if os.path.exists(default_suffix_path):
                        if os.path.exists(new_path):
                            os.remove(new_path)
                        os.rename(default_suffix_path, new_path)
                        #if backup_path is not None:
                         #   os.rename(backup_path, default_suffix_path)
                if event_manager is None:
                    if image_id not in self.gui.csp.mask_paths:
                        self.gui.csp.mask_paths[image_id] = {}
                else:
                    if image_id not in mask_paths:
                        mask_paths[image_id] = {}

                if event_manager is None:
                    self.gui.csp.mask_paths[image_id][segmentation_channel] = new_path
                else:
                    mask_paths[image_id][segmentation_channel] = new_path

                percent = round((iN + 1) / n_images * 100)
                progress = str(percent) + " %"
                if event_manager is None:
                    current_image = {"image_id": image_id, "path": image_path}
                    self._call_update_listeners(progress, current_image)
                else:
                    event_manager.notify(ProgressEvent(percent=percent,
                                                       process=f"Segmenting Images: {iN + 1}/{n_images} (Latest Image: {image_id})"))
                self.num_seg_images = self.num_seg_images + 1
                if event_manager is None:
                    self.gui.directory.update_mask_check(image_id)
                    self.gui.page.run_task(self.gui.average_diameter.get_avg_diameter, image_id)
            else:
                percent = round((iN + 1) / n_images * 100)
                progress = str(percent) + " %"
                if event_manager is None:
                    current_image = {"image_id": image_id, "path": None}
                    self._call_update_listeners(progress, current_image)
                else:
                    event_manager.notify(ProgressEvent(percent=percent,
                                                       process=f"Segmenting Images: {iN + 1}/{n_images} (Latest Image: {image_id})"))
                self.num_seg_images = self.num_seg_images + 1

        if event_manager is None:
            self._call_completion_listeners()
        else:
            event_manager.notify(ProgressEvent(percent=100, process=f"All images segmented."))
        # reset variables
        self.num_seg_images = 0


class BatchImageReadout(Notifier):

    def __init__(self,
                 image_paths,
                 mask_paths,
                 export_file_type: ExportFileType,
                 file_path: pathlib.Path,
                 segmentation_channel,
                 channel_prefix="c",
                 module: bool = False
                 ):
        if not module:
            super().__init__()

        self.image_paths = image_paths
        self.mask_paths = mask_paths
        self.export_file_type = export_file_type
        self.file_path = file_path
        self.segmentation_channel = segmentation_channel
        self.channel_prefix = channel_prefix

    def _channel_name(self, channel_id):
        return self.channel_prefix + str(channel_id)

    def run(self, event_manager: EventManager = None):
        image_paths = self.image_paths
        n_images = len(image_paths)

        if event_manager is None:
            self._call_start_listeners()
        else:
            event_manager.notify(ProgressEvent(0, f"Readout Images: 0/{n_images}"))

        mask_paths = self.mask_paths
        segmentation_channel = self.segmentation_channel

        row_entries = []

        for iN, image_id in enumerate(image_paths):

            # 1. Check if Image has Mask in mask_paths
            # 2. Iterate over all channels and skip segmentation channel
            # 3. Get Background and derive
            # 4. For each cell readout fluorescence
            # 5. Store values in a pandas dataframe "readout" (Layout: Image ID | Cell ID | Channels ... | Background)

            if not image_id in mask_paths or not segmentation_channel in mask_paths[image_id]:
                continue
            mask_path = mask_paths[image_id][segmentation_channel]
            mask_data = np.load(mask_path, allow_pickle=True).item()
            mask = mask_data["masks"].astype(np.uint16)

            cell_ids = np.unique(mask)
            if len(cell_ids) == 1:
                if event_manager is None:
                    kwargs = {"progress": str(int((iN + 1) / n_images * 100)) + "%",
                              "current_image": {"image_id": image_id}}
                    self._call_update_listeners(**kwargs)
                else:
                    event_manager.notify(ProgressEvent(percent=int((iN + 1) / n_images * 100),
                                                       process=f"Readout Images: {iN + 1}/{n_images} (Latest Image: {image_id})"))
                continue
            cell_ids = cell_ids[1:]

            channels = list(image_paths[image_id])
            n_channels = len(channels)

            cur_row_entries = [None] * len(cell_ids)
            for iX, cell_id in enumerate(cell_ids):
                data_entry = {"image_id": image_id,
                              "id": cell_id,
                              "seg_channel": segmentation_channel, }
                for channel_id in channels:
                    channel_name = self._channel_name(channel_id)
                    data_entry[channel_name] = None
                    data_entry[f"background {channel_name}"] = None

                cur_row_entries[iX] = data_entry

            for channel_id in channels:
                image_path = image_paths[image_id][channel_id]
                channel_name = self._channel_name(channel_id)

                np_image = load_image_to_numpy(image_path)
                np_image = np.squeeze(np_image)

                background_mask = mask == 0
                background_val = np.mean(np_image[background_mask])

                for iX, cell_id in enumerate(cell_ids):
                    cell_mask = mask == cell_id
                    cell_val = np.mean(np_image[cell_mask])

                    cur_row_entries[iX][channel_name] = cell_val
                    cur_row_entries[iX][f"background {channel_name}"] = background_val
            row_entries += cur_row_entries

            if event_manager is None:
                kwargs = {"progress": str(int((iN + 1) / n_images * 100)) + "%",
                          "current_image": {"image_id": image_id}}
                self._call_update_listeners(**kwargs)
            else:
                event_manager.notify(ProgressEvent(percent=int((iN + 1) / n_images * 100),
                                                   process=f"Readout Images: {iN + 1}/{n_images} (Latest Image: {image_id})"))

        readout_path = self.file_path
        df = pd.DataFrame(row_entries)

        match self.export_file_type:
            case ExportFileType.EXCEL:
                df.to_excel(readout_path, index=False)
            case ExportFileType.CSV:
                df.to_csv(readout_path, index=False)
            case ExportFileType.TSV:
                df.to_csv(readout_path, sep="\t", index=False)
            case ExportFileType.PDF:
                export_dataframe_to_pdf(df, str(readout_path.absolute()))

        if event_manager is None:
            kwargs = {}
            self._call_completion_listeners(readout=df, readout_path=readout_path, **kwargs)
        else:
            event_manager.notify(ProgressEvent(100, "Completed Readout"))
