"""Reproduce the overlapping-search speech experiment in a fresh directory."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys
from build_ima3_direct import build_verified
from ima3_series import build_volume
from probe_reconstruction_error import wav8
from verify_ima3_series import verify_series

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--fuse', type=Path, required=True)
p.add_argument('--ffmpeg', required=True)
a = p.parse_args()
out = a.output.resolve()
if out.exists() and any(out.iterdir()):
    raise ValueError('use a fresh output directory')
out.mkdir(parents=True, exist_ok=True)
encoder = Path(__file__).resolve().parents[2]/'ima_waveform_encoder.py'
subprocess.run([sys.executable, str(encoder), '--input', str(a.reference), '--output', str(out/'encode'),
                '--ima3', '--width', '256', '--block-size', '128', '--commit-size', '64',
                '--regularization', '.03', '--ffmpeg', a.ffmpeg], check=True)
packed = gzip.decompress((out/'encode/soundtrack.ima.gz').read_bytes())
build_verified(wav8(a.reference/'source-preview.wav'), packed, out/'qualified', a.fuse, a.ffmpeg)
disk, meta = build_volume([out/'qualified']*2, out/'disk', bytes(range(48, 64)), 1, 1)
(out/'audio.trd').write_bytes(disk)
(out/'volumes.json').write_text(json.dumps([dict(file='audio.trd', **meta)], indent=2)+'\n', encoding='utf-8')
verify_series(out, a.fuse, a.ffmpeg)
subprocess.run([sys.executable, str(Path(__file__).with_name('record-first-part.py')),
                '--disk', str(out/'audio.trd'), '--metadata', str(out/'disk/part-01/player.json'),
                '--output', str(out/'normal'), '--fuse', str(a.fuse)], check=True)
