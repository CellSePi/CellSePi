import pickle

import subprocess
import json
import os
import pathlib
import threading
import pandas as pd
import numpy as np

from backend.constants import ExportFileType
from backend.data_util import load_image_to_numpy, export_dataframe_to_pdf
from backend.expert_mode.event_manager import EventManager
from backend.expert_mode.listener import ProgressEvent
from backend.notifier import Notifier
from backend.settings import SettingsManager
from backend.worker_util import get_multi_worker_command, get_worker_env


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
        else:
            self.segmentation_channel = segmentation_channel
            self.diameter = diameter
            self.suffix = suffix

        self.masks_backup = {}
        self.prev_masks_exist = False
        self.cancel_now = False
        self.pause_now = False
        self.resume_now = False
        self.executor = None

    # the following methods handle the different actions and handle accordingly
    def cancel_action(self):
        self.cancel_now = True
        if self.executor is not None and self.executor.poll() is None:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.executor.pid)],
                    capture_output=True
                )
            else:
                self.executor.terminate()

    def pause_action(self):
        self.pause_now = True
        if self.executor is not None and self.executor.poll() is None:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.executor.pid)],
                    capture_output=True
                )
            else:
                self.executor.terminate()

    def resume_action(self):
        self.resume_now = True

    def run(self, event_manager: EventManager = None, image_paths=None, mask_paths=None, model_path=None,
            model_type=None,cancel_event=None):
        """
        Applies the segmentation model to every image and stores the resulting masks.
        """
        if event_manager is None:
            self.segmentation_channel = self.gui.csp.config.get_bf_channel()
            self.diameter = self.gui.csp.config.get_diameter()
            self.suffix = self.gui.csp.current_mask_suffix
            image_paths = self.gui.csp.image_paths
            mask_paths = self.gui.csp.mask_paths
            model_path = self.gui.csp.model_path
            model_type = self.gui.csp.model_type.value.name
            n_images = len(image_paths)
            current_done_count = sum(
                1 for img_id in mask_paths
                if self.segmentation_channel in mask_paths[img_id] and mask_paths[img_id][self.segmentation_channel] is not None
            )
            percent = int((current_done_count / n_images) * 100)
            self._call_start_listeners(f"{percent} %")
        else:
            event_manager.notify(ProgressEvent(percent=0, process="Segmentation started."))
            model_type = model_type.value.name

        settings_manager = SettingsManager()

        config = {
            "image_paths": image_paths,
            "mask_paths": mask_paths,
            "model_path": model_path,
            "model_type_str": model_type,
            "segmentation_channel": self.segmentation_channel,
            "diameter": self.diameter,
            "suffix": self.suffix,
            "gpu_flag": self.GPU,
            "delete_small_masks": settings_manager.settings.segmentation.delete_small_masks,
            "mask_deletion_diameter": settings_manager.settings.segmentation.mask_deletion_diameter,
            "rescale_settings": settings_manager.settings.performance.segmentation_downscaling.model_dump(mode="json")
        }

        cmd = get_multi_worker_command()
        cmd.append("eval")
        cmd.append(json.dumps(config))

        self.executor = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8',
            env=get_worker_env()
        )

        woke_synthetically = threading.Event()

        def cancel_listener():
            cancel_event.wait()
            if woke_synthetically.is_set():
                return
            if self.executor is not None and self.executor.poll() is None:
                self.cancel_action()

        thread = None
        if cancel_event:
            thread = threading.Thread(target=cancel_listener, daemon=True)
            thread.start()

        self.stdout_listener(event_manager, cancel_event)

        if cancel_event:
            was_real_cancel = cancel_event.is_set()
            if not was_real_cancel:
                woke_synthetically.set()
                cancel_event.set()
            thread.join()
            if not was_real_cancel:
                cancel_event.clear()

    def stdout_listener(self, event_manager,cancel_event):
        pending_error = None
        for line in iter(self.executor.stdout.readline, ''):
            if not line: break
            try:
                msg = json.loads(line)

                if msg["type"] == "progress":
                    img_id = msg["image_id"]
                    percent = msg["percent"]

                    if not msg["skipped"]:
                        if event_manager is None:
                            if img_id not in self.gui.csp.mask_paths:
                                self.gui.csp.mask_paths[img_id] = {}
                            self.gui.csp.mask_paths[img_id][self.segmentation_channel] = msg["new_path"]
                            self.gui.directory.update_mask_check(img_id)
                            self.gui.page.run_task(self.gui.average_diameter.get_avg_diameter, img_id)

                    if event_manager is None:
                        self._call_update_listeners(f"{percent} %", {"image_id": img_id})
                    else:
                        event_manager.notify(ProgressEvent(percent=percent, process=f"Segmenting: {img_id}"))

                elif msg["type"] == "error":
                    pending_error = msg

            except json.JSONDecodeError:
                print("Worker Log:", line.strip())

        self.executor.wait()

        if pending_error is not None:
            error_type = pending_error.get("error_type")
            if error_type == "UnpicklingError":
                raise pickle.UnpicklingError(pending_error["text"])
            else:
                raise RuntimeError(pending_error["text"])

        if self.cancel_now or (cancel_event and cancel_event.is_set()):
            self.cancel_now = False
        elif self.pause_now:
            self.pause_now = False
        else:
            if event_manager is None:
                self._call_completion_listeners()
            else:
                event_manager.notify(ProgressEvent(percent=100, process="All images segmented."))

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
