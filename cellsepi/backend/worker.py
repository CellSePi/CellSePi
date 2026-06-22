import os

import sys
import json

base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, base_path)

flet_env = os.environ.get("FLET_SITE_PACKAGES")
if flet_env:
    try:
        flet_paths = json.loads(flet_env)
        for p in reversed(flet_paths):
            if p and p not in sys.path:
                sys.path.insert(0, p)
            if p and p not in os.environ.get("PATH", ""):
                os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
    except Exception as e:
        print(json.dumps({"type": "error", "error_type": "EnvError", "text": str(e)}), flush=True)

if __name__ == "__main__":
    if len(sys.argv) > 2:
        mode = sys.argv[1]
        config = json.loads(sys.argv[2])

        if mode == "train":
            from backend.training import run_cellpose_training
            run_cellpose_training(**config)

        elif mode == "eval":
            from backend.evaluation_logic import run_cellpose_evaluation
            run_cellpose_evaluation(**config)