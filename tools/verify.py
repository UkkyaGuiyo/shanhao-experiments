"""Reviewed test supervisor, separate from the product worker graph.

Usage: python3 -I -B this_file.py ROOT tests [unittest arguments...]
       python3 -I -B this_file.py ROOT cli [fixed CLI arguments...]

Only use against the statically reviewed, finite repository snapshot.
The file budget is checked, not an OS filesystem quota. Static write bounds
remain required. This does not create network/filesystem isolation.
"""
import time
START = time.monotonic()
import ctypes
import os
from pathlib import Path
import resource
import selectors
import signal
import stat
import subprocess
import sys

MIB = 1024 * 1024
DEADLINE = START + 10.0
OUTPUT_LIMIT = 65536
FILE_BUDGET = 32 * MIB
STATIC_GENERATION_ALLOWANCE = 8 * MIB
REPO = Path(sys.argv[1]).resolve(strict=True)
MODE = sys.argv[2]
ARGS = sys.argv[3:]
if MODE not in {"tests", "cli"}:
    raise SystemExit("only reviewed tests/cli are allowed")
if sys.version_info[:3] != (3, 12, 14) or sys.platform != "linux":
    raise SystemExit("requires Linux CPython 3.12.14")
EXE = Path(sys.executable).resolve(strict=True)
if not (REPO / "hello_world" / "limits.json").is_file():
    raise SystemExit("unexpected repository root")

def cap(address, cpu):
    for kind, value in ((resource.RLIMIT_AS, address),
                        (resource.RLIMIT_CPU, cpu),
                        (resource.RLIMIT_FSIZE, MIB),
                        (resource.RLIMIT_CORE, 0),
                        (resource.RLIMIT_NOFILE, 64)):
        resource.setrlimit(kind, (value, value))
        if resource.getrlimit(kind) != (value, value):
            raise RuntimeError("resource limit mismatch")

def worker_cap():
    cap(192 * MIB, 8)

def generated_bytes():
    """Metadata only; never follow test symlinks or open a FIFO."""
    folder = REPO / ".hello-world"
    if folder.is_symlink():
        raise RuntimeError("symlink work root refused")
    total = 0
    pending = [folder] if folder.exists() else []
    while pending:
        if time.monotonic() >= DEADLINE:
            raise TimeoutError("10-second outer deadline exceeded")
        current = pending.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                try:
                    info = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue  # Test-owned cleanup can remove its own entries.
                if stat.S_ISDIR(info.st_mode):
                    pending.append(Path(entry.path))
                elif stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                    total += info.st_size
                if total > FILE_BUDGET:
                    raise RuntimeError("generated file budget exceeded")
    return total

def direct_children():
    # This runtime exposes /proc/PID/stat, but not task/PID/children.
    children = []
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit():
            continue
        try:
            record = Path(entry.path, "stat").read_text()
        except FileNotFoundError:
            continue
        parent = int(record.rsplit(")", 1)[1].split()[1])
        if parent == os.getpid():
            children.append(int(entry.name))
    return children

def cleanup_descendants():
    """Subreaper adoption also covers children that started a new session."""
    while True:
        children = direct_children()
        if not children:
            return
        for pid in children:
            # No concurrent reaper exists; listed children cannot be reused
            # before waitpid below, including children that are already zombies.
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for pid in children:
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass

available = os.sched_getaffinity(0)
if not available:
    raise SystemExit("affinity unavailable")
os.sched_setaffinity(0, {min(available)})
if len(os.sched_getaffinity(0)) != 1:
    raise SystemExit("single CPU not enforced")
libc = ctypes.CDLL(None, use_errno=True)
if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
    raise SystemExit("subreaper unavailable")
enabled = ctypes.c_int()
if libc.prctl(37, ctypes.byref(enabled), 0, 0, 0) != 0 or enabled.value != 1:
    raise SystemExit("subreaper not verified")
direct_children()  # Fail closed before launch if process metadata is absent.
if generated_bytes() + STATIC_GENERATION_ALLOWANCE > FILE_BUDGET:
    raise SystemExit("insufficient remaining static generated-file budget")

# Launch before lowering this process to 64 MiB. The test worker is capped
# before exec, and its CLI descendants can still set their reviewed own caps.
launcher = """
import os, runpy, sys
root, mode, *args = sys.argv[1:]
os.chdir(root)
sys.path.insert(0, root)
if mode == 'tests':
    import unittest
    unittest.main(module=None, argv=['unittest', *args])
else:
    sys.argv = ['hello_world.cli', *args]
    runpy.run_module('hello_world.cli', run_name='__main__')
"""
environment = {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
               "PATH": str(EXE.parent) + ":/usr/bin:/bin",
               "PYTHONDONTWRITEBYTECODE": "1"}
stdout, stderr = bytearray(), bytearray()
result = 125
problem = None
child = None
try:
    child = subprocess.Popen(
        [str(EXE), "-I", "-B", "-c", launcher, str(REPO), MODE, *ARGS],
        cwd=REPO, env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True, close_fds=True, preexec_fn=worker_cap,
    )
    cap(64 * MIB, 2)
    with selectors.DefaultSelector() as selector:
        selector.register(child.stdout, selectors.EVENT_READ, stdout)
        selector.register(child.stderr, selectors.EVENT_READ, stderr)
        while selector.get_map():
            remaining = DEADLINE - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("10-second outer deadline exceeded")
            for key, _ in selector.select(min(remaining, 0.05)):
                block = os.read(key.fileobj.fileno(), 4096)
                if not block:
                    selector.unregister(key.fileobj)
                elif len(stdout) + len(stderr) + len(block) > OUTPUT_LIMIT:
                    raise RuntimeError("64 KiB outer output budget exceeded")
                else:
                    key.data.extend(block)
        remaining = DEADLINE - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("10-second outer deadline exceeded")
        result = child.wait(timeout=remaining)
    generated_bytes()
except (OSError, RuntimeError, ValueError, TimeoutError,
        subprocess.TimeoutExpired, MemoryError) as error:
    problem = ("outer supervisor refused: " + str(error)[:256] + "\n").encode()
    result = 125
finally:
    cleanup_descendants()
    if child is not None and child.stdout is not None:
        child.stdout.close()
        child.stderr.close()
if problem:
    # Diagnostic and captured bytes still share one 64 KiB output allowance.
    available = max(0, OUTPUT_LIMIT - len(problem))
    stdout = stdout[:available]
    stderr = stderr[:max(0, available - len(stdout))] + problem
sys.stdout.buffer.write(stdout)
sys.stderr.buffer.write(stderr)
raise SystemExit(result if 0 <= result <= 255 else 1)
