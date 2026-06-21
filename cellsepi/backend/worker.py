import sys
import json

if __name__ == "__main__":
    if len(sys.argv) > 2:
        mode = sys.argv[1]
        config = json.loads(sys.argv[2])

        if mode == "train":
            from backend.training import run_cellpose_training
            run_cellpose_training(**config)

        #elif mode == "eval":
        #    from backend.evaluation_logic import run_cellpose_evaluation
        #    run_cellpose_evaluation(**config)