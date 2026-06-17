import argparse
import json
import sys
print(json.dumps({"type": "log", "text": ">>> FIRST ROW"}), flush=True)
sys.stdout.flush()
import logging

from cellpose import models, train, io

from backend.CellposeV3 import modelsV3, trainV3
from backend.constants import ModelType

def send_to_gui(msg_dict):
    print(json.dumps(msg_dict), flush=True)

def _last_logged_epoch(n):
    for i in range(n - 1, -1, -1):
        if i == 5 or i % 10 == 0:
            return i
    return 0

class JSONLogHandler(logging.Handler):

    def __init__(self, total_epochs):
        super().__init__()
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
            send_to_gui({"type": "epoch", "text": log_msg, "percent": percent})
            if current_epoch >= self.last_possible:
                self.last_epoch_logged = True
        elif "saving network parameters" in log_msg and self.last_epoch_logged:
            send_to_gui({"type": "epoch", "text": f"epochs {self.total_epochs}/{self.total_epochs}, {log_msg}",
                        "percent": 1.0})
        else:
            send_to_gui({"type": "log", "text": log_msg})

class JSONTqdmStream:
    def write(self, text):
        clean_text = text.replace('\r', '').replace('\n', '').strip()
        if clean_text:
            if "%" in text or "it/" in text:
                parsed = self._parse_tqdm(clean_text)
                send_to_gui({"type": "tqdm", "text": clean_text, **parsed})
            else:
                send_to_gui({"type": "log", "text": clean_text})

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_type_name", type=str, required=True)
    parser.add_argument("--working_dir", type=str, required=True)
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument("--learning_rate", type=float, required=True)
    parser.add_argument("--weight", type=float, required=True)
    parser.add_argument("--diameter", type=float, required=True)
    parser.add_argument("--model_name", type=str, required=True)
    parser.add_argument("--save_path", type=str, required=True)
    parser.add_argument("--gpu", type=int, required=True)
    parser.add_argument("--sgd", type=int, required=True)
    parser.add_argument("--pretrained_path", type=str, default=None)
    parser.add_argument("--mask_suffix", type=str, required=True)

    args = parser.parse_args()

    model_type = next((m for m in ModelType if m.value.name == args.model_type_name), None)
    gpu_flag = bool(args.gpu)
    sgd_value = bool(args.sgd)
    mask_filter = f"{args.mask_suffix}.npy"
    pretrained_path = args.pretrained_path if args.pretrained_path != "None" else None

    cellpose_logger = logging.getLogger()
    cellpose_logger.handlers.clear()
    cellpose_logger.addHandler(JSONLogHandler(args.epochs))
    cellpose_logger.setLevel(logging.INFO)
    sys.stderr = JSONTqdmStream()

    try:
        send_to_gui({"type": "log", "text": ">>> Training started. Loading images and masks..."})

        if model_type == ModelType.CP_CYTO or model_type == ModelType.CP_NUCLEI:
            from backend.CellposeV3 import ioV3

            output = ioV3.load_train_test_data(train_dir=args.working_dir, mask_filter=mask_filter,
                                               look_one_level_down=False)
        elif model_type == ModelType.CP_SAM:
            output = io.load_train_test_data(train_dir=args.working_dir, mask_filter=mask_filter,
                                             look_one_level_down=False)
        else:
            send_to_gui({"type": "error", "text": "Custom Model not supported yet!", "error_obj": str("")})
            sys.exit(1)

        images, labels, image_names, test_images, test_labels, image_names_test = output

        if len(images) == 0 or len(labels) == 0:
            send_to_gui({"type": "error", "text": "You need images and suitable masks to train a model!", "error_obj": str("")})
            sys.exit(1)

        if model_type == ModelType.CP_SAM:
            model = models.CellposeModel(
                diam_mean=args.diameter,
                pretrained_model=pretrained_path if sgd_value else None,
                gpu=gpu_flag
            )
            train.train_seg(model.net, train_data=images, train_labels=labels, normalize=True,
                            test_data=test_images, test_labels=test_labels, weight_decay=args.weight, SGD=sgd_value,
                            learning_rate=args.learning_rate, n_epochs=args.epochs, model_name=args.model_name,
                            save_path=args.save_path)
        else:
            model = modelsV3.CellposeModel(
                diam_mean=args.diameter,
                pretrained_model=pretrained_path if sgd_value else None,
                model_type="cyto3" if model_type == ModelType.CP_CYTO else "nuclei",
                gpu=gpu_flag
            )
            trainV3.train_seg(model.net, train_data=images, train_labels=labels, channels=[0, 0], normalize=True,
                              test_data=test_images, test_labels=test_labels, weight_decay=args.weight, SGD=sgd_value,
                              learning_rate=args.learning_rate, n_epochs=args.epochs, model_name=args.model_name,
                              save_path=args.save_path)

        send_to_gui({"type": "finished", "text": "Finished Training"})
        sys.exit(0)

    except Exception as e:
        send_to_gui({"type": "error", "text": "Something went wrong while training!", "error_obj": str(e)})
        sys.exit(1)

