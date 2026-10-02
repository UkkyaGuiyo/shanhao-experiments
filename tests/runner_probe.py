"""Test-only supervisor for fixed, reviewed resource fixtures; never public CLI."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hello_world import sandbox
sandbox.WORKER_PATH = Path(__file__).with_name("worker_probe.py")
# A reviewed fixture infers its kind from the unique run ID.
if sys.argv[1] == "timeout":
    sandbox.WALL_SECONDS = 1.0
result = sandbox.run_bounded(["stage", sys.argv[2], "proposal"])
sys.stderr.buffer.write(result.stderr)
print(result.code)
