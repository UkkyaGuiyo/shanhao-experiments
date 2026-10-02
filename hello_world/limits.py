"""Process-local limits, not a general-purpose security sandbox."""
import json
import os
from pathlib import Path
import resource
from hello_world.safeio import read_regular

MiB = 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]
# The checked-in description must agree with these reviewed ceilings.
EXPECTED = {
    "mode": "smoke", "wall_seconds": 10, "cpu_count": 1,
    "worker_cpu_seconds": 8, "supervisor_cpu_seconds": 2,
    "worker_address_space_bytes": 192 * MiB,
    "supervisor_address_space_bytes": 64 * MiB,
    "individual_file_bytes": MiB, "artifact_bytes": 65536,
    "artifact_count": 4, "captured_output_bytes": 65536,
    "generated_file_budget_bytes": 32 * MiB, "heavy_available": False,
}

def verify_configuration():
    path = ROOT / "hello_world" / "limits.json"
    if json.loads(read_regular(path, 4096)) != EXPECTED:
        raise ValueError("limit changes require a reviewed implementation change")

def one_cpu():
    available = os.sched_getaffinity(0)
    if not available:
        raise RuntimeError("CPU affinity unavailable")
    os.sched_setaffinity(0, {min(available)})
    if len(os.sched_getaffinity(0)) != 1:
        raise RuntimeError("single-CPU affinity not enforced")

def apply_limits(role):
    verify_configuration()
    one_cpu()
    address = EXPECTED[role + "_address_space_bytes"]
    cpu = EXPECTED[role + "_cpu_seconds"]
    for limit, value in ((resource.RLIMIT_AS, address), (resource.RLIMIT_CPU, cpu),
                         (resource.RLIMIT_FSIZE, MiB), (resource.RLIMIT_CORE, 0),
                         (resource.RLIMIT_NOFILE, 64)):
        resource.setrlimit(limit, (value, value))
        if resource.getrlimit(limit) != (value, value):
            raise RuntimeError("process resource limit not enforced")
    return snapshot()

def apply_worker_limits():
    return apply_limits("worker")

def snapshot():
    return {
        "address_space_bytes": resource.getrlimit(resource.RLIMIT_AS)[0],
        "cpu_seconds": resource.getrlimit(resource.RLIMIT_CPU)[0],
        "file_bytes": resource.getrlimit(resource.RLIMIT_FSIZE)[0],
        "cpus": sorted(os.sched_getaffinity(0)),
    }
