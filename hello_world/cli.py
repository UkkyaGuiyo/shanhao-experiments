"""Public entry point: all operations go through the bounded supervisor."""
import argparse
import sys
from hello_world.sandbox import run_bounded
from hello_world.storage import STAGES

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eleven motions. Five electors. Four mandatory artifacts.")
    parser.add_argument("operation", choices=("run", "stage", "show", "limits"))
    parser.add_argument("stage", nargs="?", choices=STAGES)
    parser.add_argument("--run-id", required=True, help="fresh lowercase/digit/hyphen ledger name")
    args = parser.parse_args(argv)
    if (args.operation == "stage") != (args.stage is not None):
        parser.error("a stage name is required only for the stage operation")
    request = [args.operation, args.run_id] + ([args.stage] if args.stage else [])
    try:
        result = run_bounded(request)
    except ValueError as error:
        print("runner refused: " + str(error), file=sys.stderr)
        return 2
    sys.stderr.buffer.write(result.stderr)
    if result.code == 0:
        sys.stdout.buffer.write(result.stdout)
    return result.code

if __name__ == "__main__":
    raise SystemExit(main())
