"""Use the reusable source packages without requiring a pip install here."""
from pathlib import Path
import sys

LIBRARIES = Path(__file__).resolve().parents[1] / 'libraries'
for package in ('zx0', 'lzsa'):
    source = str(LIBRARIES / package / 'src')
    if source not in sys.path:
        sys.path.insert(0, source)
