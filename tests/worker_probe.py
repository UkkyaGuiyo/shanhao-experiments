"""Finite fixtures only: no network, child creation, threads or arbitrary code."""
import errno
import json
import os
from pathlib import Path
import resource
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hello_world.limits import apply_worker_limits
apply_worker_limits()
name = sys.argv[2]
kind = name.split("-")[1]
folder = ROOT / ".hello-world" / "runs" / name
if kind == "memory":
    try:
        allocation = bytearray(256 * 1024 * 1024)
    except MemoryError:
        print("memory-denied", file=sys.stderr)
    else:
        raise SystemExit(90)
elif kind == "file":
    try:
        with (folder / "fixture.bin").open("wb") as output:
            output.write(b"x" * (1024 * 1024 + 1))
    except OSError as error:
        if error.errno != errno.EFBIG:
            raise
        print("file-denied", file=sys.stderr)
    else:
        raise SystemExit(91)
elif kind in ("cpu", "timeout"):
    (folder / "pid").write_text(str(os.getpid()))
    if kind == "cpu":
        resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
    # Finite, deliberately exceeds the probe's CPU/deadline, never unbounded.
    total = sum(x * x for x in range(100_000_000))
    raise SystemExit(92)
elif kind == "log":
    sys.stderr.write("x" * (70 * 1024))
else:
    raise SystemExit(93)
