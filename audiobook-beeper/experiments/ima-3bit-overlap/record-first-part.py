"""Capture the normal Fuse sound path of the first part of a sequential TRD.

FMF omits its last incomplete frame at exit; this trims only the silent guard.
This listening artifact complements the complete per-pulse verification.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import wave
from record_pcm import read_fmf
from smoke_test_fuse import hidden_startupinfo

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--disk', type=Path, required=True)
p.add_argument('--metadata', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--fuse', type=Path, required=True)
a = p.parse_args()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=True)
meta = json.loads(a.metadata.read_bytes())
labels = meta['player_labels']
lines = ['base 10', 'set $started 0']
events = [(labels['ready'], ['print 100', 'print spectrum:frames', 'print ula:tstates'], '')]
events += [(address+2, ['print 101', 'print spectrum:frames', 'print ula:tstates', 'set $started 1'],
            '$started==0') for address in meta['first_addresses']]
events += [(labels['chain_exit'], ['print 200', 'print spectrum:frames', 'print ula:tstates', 'exit 77'], '')]
for number, (address, body, condition) in enumerate(events, 1):
    lines += [f'breakpoint {address}', f'commands {number}', *body, 'continue', 'end']
    if condition:
        lines.append(f'condition {number} {condition}')
script = '\n'.join(lines)
(out/'debugger.txt').write_text(script, encoding='utf-8')
movie = out/'capture.fmf'
cmd = [str(a.fuse.resolve()), '--sound', '--sound-freq', '44100', '--no-autosave-settings',
       '--no-confirm-actions', '--speed', '100', '--machine', '128', '--beta128',
       '--movie-start', str(movie), '--movie-compr', 'None', '--debugger-command', script, str(a.disk.resolve())]
result = subprocess.run(cmd, cwd=a.fuse.resolve().parent, capture_output=True, timeout=150,
                        startupinfo=hidden_startupinfo(),
                        env=dict(os.environ, SDL_AUDIODRIVER='dummy', SDL_VIDEODRIVER='dummy'))
(out/'trace.txt').write_bytes(result.stdout)
(out/'stderr.txt').write_bytes(result.stderr)
assert result.returncode == 77
numbers = iter(int(m.group(1), 0) for m in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$', result.stdout))
observed = {}
for tag in numbers:
    assert tag not in observed
    observed[tag] = (next(numbers), next(numbers))
assert set(observed) == {100, 101, 200}
blob = movie.read_bytes()
(out/'capture.fmf.gz').write_bytes(gzip.compress(blob, mtime=0))
raw, chunks, timing = read_fmf(blob)
assert timing == 'B'
frame, tick = observed[101]
chunk = next(c for c in chunks if c[0] == frame)
start = chunk[1]+round(chunk[2]*tick/70908)
pcm = raw[start:]
with wave.open(str(out/'result-preview.wav'), 'wb') as stream:
    stream.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
    stream.writeframes(pcm.tobytes())
report = dict(normal_fuse_sound=True, speed_percent=100, host_audio_muted=True,
              first_part_reached_exit=True, events=observed, output_samples=len(pcm),
              playback_seconds=len(pcm)/44100, partial_final_guard_frame_omitted=True,
              audio_timebase_unmodified=True, trd_sha256=hashlib.sha256(a.disk.read_bytes()).hexdigest(),
              fuse_sha256=hashlib.sha256(a.fuse.read_bytes()).hexdigest())
(out/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report))
