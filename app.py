"""
EVOFORGE Streamlit launcher.

This project has been split into a modular folder structure.
For safety, the current working app is preserved in legacy/runtime.py and run
directly. The modules are ready for progressive migration without breaking
the deployed app.
"""

from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "legacy" / "runtime.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if not RUNTIME.exists():
    import streamlit as st
    st.error("EVOFORGE runtime file not found.")
    st.code(str(RUNTIME))
    st.stop()

runpy.run_path(str(RUNTIME), run_name="__main__")
