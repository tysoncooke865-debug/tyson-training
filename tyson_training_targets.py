from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "legacy" / "runtime.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

runpy.run_path(str(RUNTIME), run_name="__main__")
