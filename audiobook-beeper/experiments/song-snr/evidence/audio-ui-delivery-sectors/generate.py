"""Fresh full C generation using the shared source/PLAYER identity checks.

The initial frame-clock output stays immutable. This wrapper selects a new
directory for the sector-count fix and reuses the authenticated generator.
"""
from pathlib import Path
import runpy
import sys


HERE=Path(__file__).resolve().parent


if __name__=='__main__':
    if '--output' not in sys.argv:
        sys.argv+=['--output',str(HERE/'generated')]
    runpy.run_path(str(HERE.parent/'audio-ui-delivery/generate.py'),run_name='__main__')
