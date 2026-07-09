"""
EVOFORGE app entrypoint.

This Phase 1 modular refactor keeps the current tested Streamlit runtime intact
while moving the project into a clean multi-file structure. Future changes should
go into evoforge/modules/* first, then progressively replace legacy/runtime.py.
"""

from evoforge.legacy.runner import run_app

run_app()
