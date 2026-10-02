import shutil
import subprocess
import sys
import uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def new_run():
    name = "test-" + uuid.uuid4().hex
    return name, ROOT / ".hello-world" / "runs" / name

def cli(*args, root=ROOT):
    return subprocess.run([sys.executable, "-B", "-m", "hello_world.cli", *args], cwd=root, capture_output=True, timeout=12)

def remove_run(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
