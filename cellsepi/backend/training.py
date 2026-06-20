import traceback

import sys
import logging
import torch

from backend.constants import ModelType


def _last_logged_epoch(n):
    for i in range(n - 1, -1, -1):
        if i == 5 or i % 10 == 0:
            return i
    return 0


class QueueLogHandler(logging.Handler):

    def __init__(self, q, total_epochs):
        super().__init__()
        self.q = q
        self.total_epochs = total_epochs
        self.last_possible = _last_logged_epoch(total_epochs)
        self.last_epoch_logged = False

    def emit(self, record):
        log_msg = self.format(record)
        parts = log_msg.split(', ', 1)
        if len(parts) == 2 and parts[0].isdigit() and "train_loss" in parts[1]:
            current_epoch = int(parts[0])
            percent = current_epoch / self.total_epochs
            log_msg = f"epochs {current_epoch}/{self.total_epochs}, {parts[1]}"
            self.q.put({"type": "epoch", "text": log_msg, "percent": percent})
            if current_epoch >= self.last_possible:
                self.last_epoch_logged = True
        elif "saving network parameters" in log_msg and self.last_epoch_logged:
            self.q.put({"type": "epoch", "text": f"epochs {self.total_epochs}/{self.total_epochs}, {log_msg}",
                        "percent": 1.0})
        else:
            self.q.put({"type": "log", "text": log_msg})


class QueueTqdmStream:
    def __init__(self, q):
        self.q = q
        self.original_stderr = sys.__stderr__

    def write(self, text):
        if self.original_stderr:
            try:
                self.original_stderr.write(text)
                self.original_stderr.flush()
            except AttributeError:
                pass

        clean_text = text.replace('\r', '').replace('\n', '').strip()
        if clean_text:
            if "%" in text or "it/" in text:
                parsed = self._parse_tqdm(clean_text)
                self.q.put({"type": "tqdm", "text": clean_text, **parsed})
            else:
                self.q.put({"type": "log", "text": clean_text})

    def _parse_tqdm(self, text):
        import re
        result = {"percent": None, "current": None, "total": None, "elapsed": None}
        match = re.search(r'(\d+)%\|.*?\|\s*(\d+)/(\d+)\s*\[([^\]]+)\]', text)
        if match:
            result["percent"] = int(match.group(1)) / 100
            result["current"] = int(match.group(2))
            result["total"] = int(match.group(3))
            result["elapsed"] = match.group(4)
        return result

    def flush(self):
        pass


def run_cellpose_training(q, model_type_str, working_dir, mask_filter, weight, sgd_value, learning_rate,
                          epochs, model_name, save_path, gpu_flag, pretrained_path, diameter):
    cellpose_logger = logging.getLogger()
    cellpose_logger.handlers.clear()
    log_handler = QueueLogHandler(q, epochs)
    cellpose_logger.addHandler(log_handler)
    cellpose_logger.setLevel(logging.INFO)
    sys.stderr = QueueTqdmStream(q)

    try:
        model_type = None
        for elem in ModelType:
            if elem.value.name == model_type_str:
                model_type = elem
                break

        if model_type is None:
            q.put({"type": "error", "text": f"Model type {model_type_str} not supported!", "error_trace": ""})
            return

        # 2. DAS MODELL VALIDIEREN (Dein w2_data Check)
        if pretrained_path:
            q.put({"type": "log", "text": ">>> Validating pretrained model..."})
            try:
                state_dict = torch.load(
                    pretrained_path,
                    weights_only=False,
                    map_location=torch.device("cuda" if gpu_flag else "cpu")
                )
                w2_data = state_dict.get('W2', None)

                if w2_data is None:
                    model_type = ModelType.CP_CYTO
                else:
                    model_type = ModelType.CP_SAM

            except Exception as e:
                q.put({"type": "error", "text": "Failed to load pretrained model!",
                       "error_trace": traceback.format_exc()})
                return


        q.put({"type": "log", "text": ">>> Loading images and masks..."})

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
            q.put({"type": "error", "text": "Custom Model not supported yet!", "error_obj": ""})
            return

        images, labels, image_names, test_images, test_labels, image_names_test = output

        if len(images) == 0 or len(labels) == 0:
            q.put({"type": "error", "text": "You need images and suitable masks to train a model!", "error_obj": ""})
            return

        q.put({"type": "log", "text": f">>> Loaded {len(images)} images and {len(labels)} masks, starting training..."})

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

        q.put({"type": "finished", "text": "Finished Training"})

    except Exception:
        error_trace = traceback.format_exc()
        q.put({"type": "error", "text": "Something went wrong while training! Pls look into the logs.", "error_trace": error_trace})

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