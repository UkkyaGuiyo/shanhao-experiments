"""One reviewed worker with limits. Deliberately NOT an OS-isolation sandbox.

run_bounded lowers limits/affinity on its calling supervisor process. Use via
CLI or a disposable process, never from a long-lived application.
"""
from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
from hello_world.limits import EXPECTED, ROOT, apply_limits, one_cpu, verify_configuration
from hello_world.storage import STAGES, prepare_directory, valid_run_id

WORKER_PATH = ROOT / "hello_world" / "worker.py"
WALL_SECONDS = EXPECTED["wall_seconds"]
OUTPUT_BUDGET = EXPECTED["captured_output_bytes"]

@dataclass(frozen=True)
class RunResult:
    code: int
    stdout: bytes
    stderr: bytes
    elapsed_seconds: float

def validate_arguments(argv, mode):
    if mode != "smoke":
        raise ValueError("only low-load smoke mode exists; heavy mode is unavailable")
    if not isinstance(argv, list) or len(argv) not in (2, 3) or not all(isinstance(x, str) for x in argv):
        raise ValueError("expected a fixed operation and run-id")
    operation, name, *arguments = argv
    if not valid_run_id(name):
        raise ValueError("invalid run-id")
    if operation == "stage":
        if len(arguments) != 1 or arguments[0] not in STAGES:
            raise ValueError("unknown stage")
    elif operation not in ("run", "show", "limits") or arguments:
        raise ValueError("arbitrary commands are not supported")

def run_bounded(argv: list[str], mode: str = "smoke", confirm_heavy: bool = False) -> RunResult:
    validate_arguments(argv, mode)
    start = time.monotonic()
    child = None
    lock = None
    stdout, stderr = bytearray(), bytearray()
    try:
        verify_configuration()
        directory = prepare_directory(argv[1])
        # One run-id has one writer. The lock is outside canonical artifacts.
        lock_directory = directory.parent.parent / "locks"
        if lock_directory.is_symlink():
            raise ValueError("symlink lock directory refused")
        lock_directory.mkdir(mode=0o700, exist_ok=True)
        lock = os.open(lock_directory / (argv[1] + ".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        one_cpu()
        child = subprocess.Popen(
            [sys.executable, "-I", "-B", str(WORKER_PATH), *argv],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=ROOT, env={"LANG": "C.UTF-8", "PATH": "/usr/bin:/bin"},
            start_new_session=True, close_fds=True,
        )
        # Spawn before lowering this launcher's cap, so the worker can set its own 192 MiB cap.
        # The settings are per process, not a cgroup or whole-machine guarantee.
        supervisor = apply_limits("supervisor")
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ, stdout)
            selector.register(child.stderr, selectors.EVENT_READ, stderr)
            while selector.get_map():
                remaining = WALL_SECONDS - (time.monotonic() - start)
                if remaining <= 0:
                    raise TimeoutError("10-second execution deadline exceeded")
                for key, _ in selector.select(min(remaining, 0.05)):
                    data = os.read(key.fileobj.fileno(), 4096)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    if len(stdout) + len(stderr) + len(data) > OUTPUT_BUDGET:
                        raise ValueError("captured output budget exceeded")
                    key.data.extend(data)
        remaining = max(0.001, WALL_SECONDS - (time.monotonic() - start))
        code = child.wait(timeout=remaining)
        if code != 0:
            raise ValueError("worker failed with status " + str(code))
        expected = b"HELLO WORLD\n" if argv[0] in ("run", "show") else b""
        if stdout != expected:
            raise ValueError("worker output contract violated")
        if argv[0] == "limits":
            stderr = bytearray((json.dumps({"worker": json.loads(stderr), "supervisor": supervisor}, sort_keys=True) + "\n").encode())
        return RunResult(0, bytes(stdout), bytes(stderr), time.monotonic() - start)
    except (ValueError, OSError, RuntimeError, TimeoutError, subprocess.TimeoutExpired, MemoryError) as error:
        message = ("runner refused: " + str(error)[:256] + "\n").encode("utf-8", errors="replace")
        return RunResult(1, b"", bytes(stderr[:max(0, OUTPUT_BUDGET - len(message))]) + message, time.monotonic() - start)
    finally:
        if child is not None:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            child.wait()
            child.stdout.close()
            child.stderr.close()
        if lock is not None:
            os.close(lock)
