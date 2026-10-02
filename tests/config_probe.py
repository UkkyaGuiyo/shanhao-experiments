"""Read-only probe: malformed configuration must fail before any worker starts."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hello_world import limits
limits.ROOT = Path(sys.argv[1])
try:
    limits.verify_configuration()
except (ValueError, OSError) as error:
    print(type(error).__name__)
    raise SystemExit(1)
raise SystemExit(0)
