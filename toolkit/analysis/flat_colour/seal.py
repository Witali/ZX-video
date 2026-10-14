"""Pin exact visual experiment producers and artifacts, excluding local caches."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import cv2
import numpy as np
import PIL

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRODUCERS = ('toolkit/flat_colour.py', 'toolkit/test_flat_colour.py',
    'toolkit/generic_cell_codebook.py', 'toolkit/convert_video.py',
    'toolkit/five_level_dither.py', 'toolkit/stable_colour.py',
    'toolkit/cell_palette_quality.py', 'toolkit/analysis/flat_colour/probe.py',
    'toolkit/analysis/flat_colour/measure_packets.py', 'toolkit/analysis/flat_colour/seal.py')


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    destination = HERE/'evidence/producer-sources'
    for name in PRODUCERS:
        target = destination/name;target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    for trial in ('initial-trial', 'unbounded-contour-trial', 'evidence'):
        directory = HERE/trial
        report = json.loads((directory/'report.json').read_bytes())
        files = sorted(path for path in directory.rglob('*') if path.is_file()
            and path.name != 'manifest.json' and '__pycache__' not in path.parts)
        manifest = dict(date='2026-10-14', trial=trial, source_sha256=report['source_sha256'],
            baseline_states_sha256=report['baseline_states_sha256'],
            runtime=dict(python=sys.version, numpy=np.__version__, opencv=cv2.__version__, pillow=PIL.__version__),
            scope='Authenticated host visual references and packet tests; no new native/Fuse/TRD release qualification.',
            files=[dict(path=str(path.relative_to(directory)).replace('\\', '/'),
                bytes=path.stat().st_size, sha256=digest(path)) for path in files])
        (directory/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
        print(trial, len(files), sum(path.stat().st_size for path in files))


if __name__ == '__main__':main()
