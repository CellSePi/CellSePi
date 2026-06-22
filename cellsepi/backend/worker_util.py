import json

import sys
import os
import pathlib


def get_multi_worker_command():
    exe_name = "worker.exe" if os.name == "nt" else "worker"
    base_path = pathlib.Path(__file__).parent.parent
    exe_dir = pathlib.Path(sys.executable).parent
    worker_exe = exe_dir / exe_name

    if worker_exe.exists():
        return [str(worker_exe)]
    else:
        worker_script = base_path / "backend" / "worker.py"
        return [sys.executable, str(worker_script)]

def get_worker_env() -> dict:
    env = os.environ.copy()

    env.pop("LD_LIBRARY_PATH", None)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    
    if "FLET_SITE_PACKAGES" in env:
        try:
            existing = json.loads(env["FLET_SITE_PACKAGES"])
            extra = os.pathsep.join(existing)
            env["PATH"] = extra + os.pathsep + env.get("PATH", "")
        except Exception:
            pass
        return env

    all_paths = [p for p in sys.path if p]

    if all_paths:
        env["FLET_SITE_PACKAGES"] = json.dumps(all_paths)
        extra = os.pathsep.join(all_paths)
        env["PATH"] = extra + os.pathsep + env.get("PATH", "")

    return env