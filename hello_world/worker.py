"""Fixed worker. Run through cli; this file is not a security boundary."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hello_world.limits import apply_worker_limits

# Enforce process limits before importing or executing any weekly code.
limits = apply_worker_limits()
from hello_world.pipeline import STAGES, display, run_stage
from hello_world.storage import RUNS_ROOT, valid_run_id

try:
    operation, name, *arguments = sys.argv[1:]
    if not valid_run_id(name):
        raise ValueError("invalid run-id")
    path = RUNS_ROOT / name
    if operation == "run" and not arguments:
        for stage in STAGES:
            run_stage(stage, path)
            print("enacted stage: " + stage, file=sys.stderr)
        output = display(path)
    elif operation == "stage" and len(arguments) == 1:
        run_stage(arguments[0], path)
        print("enacted stage: " + arguments[0], file=sys.stderr)
        output = b""
    elif operation == "show" and not arguments:
        output = display(path)
    elif operation == "limits" and not arguments:
        print(json.dumps(limits, sort_keys=True), file=sys.stderr)
        output = b""
    else:
        raise ValueError("unsupported operation")
    sys.stdout.buffer.write(output)
except (ValueError, OSError, KeyError, TypeError, MemoryError) as error:
    print("worker refused: " + str(error)[:256], file=sys.stderr)
    raise SystemExit(1)
