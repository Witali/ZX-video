"""Shared bounded waveform searches for the two packed IMA alphabets.

Host scores rank candidates only. Callers must execute the selected streams
on their own calibrated clocks and retain the best completely verified disk.
"""
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BALANCED = ((256, .03, 128), (512, .03, 128), (1024, .03, 256))
# Preserve the strongest old IMA3 search as a control, then vary its prior.
# Four-bit branches are more numerous, so use a smaller beam for its first
# candidate and a wider/longer search for subsequent candidates.
BEST = {
    'ima3': ((1024, .03, 256), (1024, .003, 256), (1024, .1, 256)),
    'ima4': ((256, .1, 128), (512, .03, 128), (512, .003, 256)),
}


def search_plan(codec, quality='best', attempts=3):
    if codec not in BEST or quality not in ('balanced', 'best') or attempts not in (1, 2, 3):
        raise ValueError('invalid codec, quality or bounded search count')
    return (BEST[codec] if quality == 'best' else BALANCED)[:attempts]


def host_search(pilot, out, width, weight, block_size, ffmpeg, codec='ima3'):
    if codec not in BEST:
        raise ValueError('unknown IMA alphabet')
    command = [sys.executable, str(HERE/'ima_waveform_encoder.py'),
               '--input', str(pilot), '--output', str(out), '--width', str(width),
               '--regularization', str(weight), '--block-size', str(block_size),
               '--commit-size', '64', '--ffmpeg', str(ffmpeg)]
    if codec == 'ima3':
        command.append('--ima3')
    subprocess.run(command, check=True)
    return json.loads((out/'report.json').read_bytes())


def ranked_hosts(hosts, limit=2):
    """Bound expensive disk executions; never treat a host score as a pass."""
    return sorted(hosts, key=lambda h: h['host_fixed_clock_snr_db'], reverse=True)[:limit]
