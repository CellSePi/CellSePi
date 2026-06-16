import sys

import logging
import queue

from cellpose import models, train

from backend.CellposeV3 import modelsV3, trainV3
from backend.constants import ModelType


class QueueLogHandler(logging.Handler):
    def __init__(self, q, total_epochs):
        super().__init__()
        self.q = q
        self.total_epochs = total_epochs

    def emit(self, record):
        log_msg = self.format(record)
        parts = log_msg.split(', ', 1)
        if len(parts) == 2 and parts[0].isdigit() and "train_loss" in parts[1]:
            current_epoch = int(parts[0])
            percent = current_epoch / self.total_epochs
            log_msg = f"epochs {current_epoch}/{self.total_epochs}, {parts[1]}"
            self.q.put({"type": "epoch", "text": log_msg, "percent": percent})
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

def run_cellpose_training(q, model_type, images, labels, test_images, test_labels, weight, sgd_value, learning_rate,
                          epochs, model_name, save_path, gpu_flag, pretrained_path, diameter):
    cellpose_logger = logging.getLogger()
    log_handler = QueueLogHandler(q, epochs)
    cellpose_logger.addHandler(log_handler)
    cellpose_logger.setLevel(logging.INFO)
    sys.stderr = QueueTqdmStream(q)

    try:
        if model_type == ModelType.CP_SAM:
            if sgd_value:
                model = models.CellposeModel(diam_mean=diameter,pretrained_model=pretrained_path if sgd_value else None, gpu=gpu_flag)
            else:
                model = models.CellposeModel(diam_mean=diameter,gpu=gpu_flag)

            train.train_seg(model.net, train_data=images, train_labels=labels, normalize=True,
                            test_data=test_images, test_labels=test_labels, weight_decay=weight, SGD=sgd_value,
                            learning_rate=learning_rate, n_epochs=epochs, model_name=model_name,
                            save_path=save_path)
        else:
            if sgd_value:
                model = modelsV3.CellposeModel(diam_mean=diameter,pretrained_model=pretrained_path, gpu=gpu_flag)
            else:
                model = modelsV3.CellposeModel(diam_mean=diameter,model_type="cyto3" if model_type == ModelType.CP_CYTO else "nuclei",
                                               gpu=gpu_flag)
            trainV3.train_seg(model.net, train_data=images, train_labels=labels, channels=[0, 0], normalize=True,
                              test_data=test_images, test_labels=test_labels, weight_decay=weight, SGD=sgd_value,
                              learning_rate=learning_rate, n_epochs=epochs, model_name=model_name,
                              save_path=save_path,)

        q.put({"type": "epoch", "text": f"epochs {epochs}/{epochs}, Training complete", "percent": 1.0})
        q.put({"type": "finished", "text": "Finished Training"})

    except Exception as e:
        q.put({"type": "error", "text": "Something went wrong while training!", "error_obj": e})
