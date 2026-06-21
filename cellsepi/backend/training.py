import time
import traceback
import json
import sys
import logging
import torch

from backend.model_types import ModelType

def _last_logged_epoch(n):
    for i in range(n - 1, -1, -1):
        if i == 5 or i % 10 == 0:
            return i
    return 0

def format_time(seconds):
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"


class JsonLogHandler(logging.Handler):
    def __init__(self, total_epochs):
        super().__init__()
        self.total_epochs = total_epochs
        self.last_possible = _last_logged_epoch(total_epochs)
        self.last_epoch_logged = False
        self.start_time = None

    def emit(self, record):
        log_msg = self.format(record)
        parts = log_msg.split(', ', 1)
        if len(parts) == 2 and parts[0].isdigit() and "train_loss" in parts[1]:
            current_epoch = int(parts[0])
            percent = current_epoch / self.total_epochs

            if self.start_time is None:
                self.start_time = time.time()

            elapsed_time = time.time() - self.start_time

            if current_epoch > 0:
                time_per_epoch = elapsed_time / current_epoch
                remaining_epochs = self.total_epochs - current_epoch
                eta = remaining_epochs * time_per_epoch
                time_info = f"[{format_time(elapsed_time)}<{format_time(eta)}, {time_per_epoch:.2f}s/epoch]"
            else:
                time_info = f"[{format_time(elapsed_time)}<?, ?s/epoch]"

            log_msg = f"epochs {current_epoch}/{self.total_epochs}, {parts[1]}"
            print(json.dumps({"type": "epoch", "text": log_msg, "percent": percent, "current": current_epoch,
                              "total": self.total_epochs, "elapsed": time_info}), flush=True)

            if current_epoch >= self.last_possible:
                self.last_epoch_logged = True
        elif "saving network parameters" in log_msg and self.last_epoch_logged:
            total_time = time.time() - self.start_time
            time_per_epoch = total_time / self.total_epochs
            time_info = f"[{format_time(total_time)}<00:00, {time_per_epoch:.2f}s/epoch]"
            print(json.dumps({"type": "epoch", "text": f"epochs {self.total_epochs}/{self.total_epochs}, {log_msg}",
                              "percent": 1.0, "current": self.total_epochs, "total": self.total_epochs,
                              "elapsed": time_info}), flush=True)
        else:
            print(json.dumps({"type": "log", "text": log_msg}), flush=True)


def _parse_tqdm(text):
    import re
    result = {"percent": None, "current": None, "total": None, "elapsed": None}
    match = re.search(r'(\d+)%\|.*?\|\s*(\d+)/(\d+)\s*\[([^\]]+)\]', text)
    if match:
        result["percent"] = int(match.group(1)) / 100
        result["current"] = int(match.group(2))
        result["total"] = int(match.group(3))
        result["elapsed"] = match.group(4)
    return result


class JsonTqdmStream:
    def __init__(self):
        pass

    def write(self, text):
        clean_text = text.replace('\r', '').replace('\n', '').strip()

        if clean_text:
            if "%" in text or "it/" in text:
                parsed = _parse_tqdm(clean_text)
                print(json.dumps({"type": "tqdm", "text": clean_text, **parsed}), flush=True)
            else:
                print(json.dumps({"type": "log", "text": clean_text}), flush=True)


def run_cellpose_training(model_type_str, working_dir, mask_filter, weight, sgd_value, learning_rate,
                          epochs, model_name, save_path, gpu_flag, pretrained_path, diameter):
    cellpose_logger = logging.getLogger()
    cellpose_logger.handlers.clear()
    log_handler = JsonLogHandler(epochs)
    cellpose_logger.addHandler(log_handler)
    cellpose_logger.setLevel(logging.INFO)
    sys.stderr = JsonTqdmStream()

    try:
        model_type = None
        for elem in ModelType:
            if elem.value.name == model_type_str:
                model_type = elem
                break

        if model_type is None:
            print(json.dumps({"type": "error", "text": f"Model type {model_type_str} not supported!", "error_trace": ""}), flush=True)
            return

        if pretrained_path:
            print(json.dumps({"type": "log", "text": ">>> Validating pretrained model..."}), flush=True)
            try:
                if gpu_flag:
                    dev_str = "cuda" if torch.cuda.is_available() else ("mps" if torch.mps.is_available() else "cpu")
                else:
                    dev_str = "cpu"

                state_dict = torch.load(
                    pretrained_path,
                    weights_only=False,
                    map_location=torch.device(dev_str)
                )
                w2_data = state_dict.get('W2', None)

                if w2_data is None:
                    model_type = ModelType.CP_CYTO
                else:
                    model_type = ModelType.CP_SAM

            except Exception as e:
                print(json.dumps({"type": "error", "text": "The input for the retrained model is invalid!",
                       "error_trace": ""}), flush=True)
                return


        print(json.dumps({"type": "log", "text": ">>> Loading images and masks..."}), flush=True)

        if model_type == ModelType.CP_CYTO or model_type == ModelType.CP_NUCLEI:
            from backend.CellposeV3 import ioV3, modelsV3, trainV3
            output = ioV3.load_train_test_data(
                train_dir=working_dir,
                mask_filter=mask_filter,
                look_one_level_down=False
            )
        elif model_type == ModelType.CP_SAM:
            from cellpose import models, train, io
            output = io.load_train_test_data(
                train_dir=working_dir,
                mask_filter=mask_filter,
                look_one_level_down=False
            )
        else:
            print(json.dumps({"type": "error", "text": "Custom Model not supported yet!", "error_trace": ""}), flush=True)
            return

        images, labels, image_names, test_images, test_labels, image_names_test = output

        if len(images) == 0 or len(labels) == 0:
            print(json.dumps({"type": "error", "text": "You need images and suitable masks to train a model!", "error_trace": ""}), flush=True)
            return

        print(json.dumps({"type": "log", "text": f">>> Loaded {len(images)} images and {len(labels)} masks, starting training..."}), flush=True)

        if model_type == ModelType.CP_SAM:
            from cellpose import models, train
            if sgd_value:
                model = models.CellposeModel(
                    pretrained_model=pretrained_path,
                    gpu=gpu_flag
                )
            else:
                model = models.CellposeModel(
                    gpu=gpu_flag
                )

            train.train_seg(model.net, train_data=images, train_labels=labels, normalize=True,
                            test_data=test_images, test_labels=test_labels, weight_decay=weight, SGD=sgd_value,
                            learning_rate=learning_rate, n_epochs=epochs, model_name=model_name, min_train_masks=1,
                            save_path=save_path)
        else:
            from backend.CellposeV3 import modelsV3, trainV3
            if sgd_value:
                model = modelsV3.CellposeModel(
                    pretrained_model=pretrained_path,
                    gpu=gpu_flag
                )
            else:
                model = modelsV3.CellposeModel(
                    diam_mean=diameter,
                    model_type="cyto3" if model_type == ModelType.CP_CYTO else "nuclei",
                    gpu=gpu_flag
                )

            # handling for 3D images -> they need to be transformed into [Y, X] format for Cellpose V3
            if images[0].ndim == 3:
                images, labels = flatten_3d_to_slices(images, labels)
                if test_images:
                    test_images, test_labels = flatten_3d_to_slices(test_images, test_labels)

            trainV3.train_seg(model.net, train_data=images, train_labels=labels, channels=[0,0], normalize=True,
                              test_data=test_images, test_labels=test_labels, weight_decay=weight, SGD=sgd_value,
                              learning_rate=learning_rate, n_epochs=epochs, model_name=model_name, min_train_masks=1,
                              save_path=save_path)

        print(json.dumps({"type": "finished", "text": "Finished Training"}), flush=True)
    except Exception:
        error_trace = traceback.format_exc()
        print(json.dumps({"type": "error", "text": "Something went wrong while training! Pls look into the logs.","error_trace": error_trace}), flush=True)

def flatten_3d_to_slices(images, labels):
    flat_imgs, flat_lbls = [], []
    for img, lbl in zip(images, labels):
        if img.ndim == 3: # convert [Z, Y, X] to individual [Y, X] slices
            for z in range(img.shape[0]):
                flat_imgs.append(img[z])
                flat_lbls.append(lbl[z])
        else: # incase already in [Y, X] format
            flat_imgs.append(img)
            flat_lbls.append(lbl)
    return flat_imgs, flat_lbls