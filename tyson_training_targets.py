"""
EVOFORGE Streamlit entrypoint.

Robust to Streamlit Cloud path/layout issues.
Searches for the preserved runtime in multiple likely locations.
"""

from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent

for p in [ROOT, ROOT / "evoforge", ROOT / "evoforge" / "legacy"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

candidate_paths = [
    ROOT / "evoforge" / "legacy" / "runtime.py",
    ROOT / "legacy" / "runtime.py",
    ROOT / "runtime.py",
    ROOT / "tyson_training_targets.py",
]

runtime_path = next((p for p in candidate_paths if p.exists()), None)

if runtime_path is None:
    import streamlit as st
    st.error("EVOFORGE runtime file was not found.")
    st.write("Expected one of:")
    for p in candidate_paths:
        st.code(str(p))
    st.stop()

runpy.run_path(str(runtime_path), run_name="__main__")
