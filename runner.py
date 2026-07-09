from pathlib import Path
import runpy

def run_app() -> None:
    runtime_path = Path(__file__).with_name("runtime.py")
    runpy.run_path(str(runtime_path), run_name="__main__")
