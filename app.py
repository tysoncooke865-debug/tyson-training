"""
EVOFORGE Streamlit entrypoint.

Robust version: does not rely on Python package imports working on Streamlit Cloud.
It runs the preserved app directly from evoforge/legacy/runtime.py.
"""

from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "evoforge" / "legacy" / "runtime.py"

# Make local package imports work if you later move modules out of legacy/runtime.py.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if not RUNTIME.exists():
    raise FileNotFoundError(
        "Could not find evoforge/legacy/runtime.py. "
        "Make sure the evoforge folder was uploaded beside app.py."
    )

runpy.run_path(str(RUNTIME), run_name="__main__")
