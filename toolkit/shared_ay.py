"""Use the canonical packed sound format without shadowing toolkit modules."""
import importlib.util
from pathlib import Path
import sys

name = '_zx_canonical_ay_format'
if name not in sys.modules:
    path = Path(__file__).resolve().parents[1]/'ay-converter'/'ay_format.py'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
AyFrame = sys.modules[name].AyFrame
# Keep multiprocessing/pickle able to import this public class in a fresh
# toolkit worker; the private loader name has no importable source filename.
AyFrame.__module__ = __name__
