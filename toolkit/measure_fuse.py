"""Measure real Fuse 128K frame delivery and TR-DOS CALL duration separately."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from smoke_test_fuse import hidden_startupinfo
from validate_streaming_player import extract_file, parse_dir


def measure(fuse: Path, trd: Path, labels: dict, timeout: float) -> dict:
    image = trd.read_bytes()
    player = extract_file(image, next(e for e in parse_dir(image) if e[0] == 'PLAYER'))
    # Bracket only CALL 3D13h; ROM execution/disk time includes that CALL.
    call = 0x6000 + player.index(b'\xcd\x13\x3d', labels['read_n']-0x6000)
    events = [(labels['main_loop'], 101), (call, 102), (call+3, 103), (labels['finished'], 199)]
    events += [(labels[n], 198) for n in ('wait_packet_fill','stream_byte_fill','fatal') if n in labels]
    lines = ['base 10']
    for index, (address, event) in enumerate(events, 1):
        lines += [f'breakpoint 0x{address:04x}', f'commands {index}',
                  f'print {event}', 'print spectrum:frames * 70908 + ula:tstates',
                  ('exit 77' if event == 199 else 'exit 99' if event == 198 else 'continue'), 'end']
    env = dict(os.environ, SDL_VIDEODRIVER='dummy')
    completed = subprocess.run([str(fuse), '--no-sound', '--no-autosave-settings',
        '--no-confirm-actions', '--speed', '1000', '--machine', '128', '--beta128',
        '--debugger-command', '\n'.join(lines), str(trd)], cwd=fuse.parent,
        env=env, capture_output=True, startupinfo=hidden_startupinfo(), timeout=timeout)
    if completed.returncode != 77:
        raise RuntimeError(f'Fuse exit {completed.returncode}; {completed.stderr!r}')
    output = completed.stdout.decode(errors='replace')
    pattern = r'(?:0x[0-9a-fA-F]+|-?\d+)'
    if not any(re.fullmatch(pattern, line.strip()) for line in output.splitlines()):
        output = (fuse.parent/'stdout.txt').read_text(errors='replace')
    numbers = [int(line.strip(), 0) for line in output.splitlines() if re.fullmatch(pattern, line.strip())]
    if len(numbers) % 2: raise ValueError(f'incomplete Fuse trace: {output[-300:]}')
    frames = []; reads = []; read_start = None
    for event, timestamp in zip(numbers[::2], numbers[1::2]):
        if event == 101: frames.append(timestamp)
        elif event == 102: read_start = timestamp
        elif event == 103:
            if read_start is None: raise ValueError('unpaired ROM exit')
            reads.append(timestamp-read_start); read_start=None
    if len(frames) < 2 or not reads: raise ValueError(f'empty trace: {output[:300]}')
    intervals = [b-a for a,b in zip(frames,frames[1:])]
    return dict(machine='Fuse 1.9.0 Spectrum 128 + Beta128', clock_hz=3546900,
                frames=len(frames), frame_interval_tstates=intervals,
                frame_interval_mean_ms=sum(intervals)/len(intervals)/3546.9,
                frame_interval_max_ms=max(intervals)/3546.9,
                measured_fps=3546900*len(intervals)/sum(intervals),
                rom_call_tstates=reads, rom_call_mean_ms=sum(reads)/len(reads)/3546.9,
                rom_call_max_ms=max(reads)/3546.9,
                note='ROM CALL durations include CALL instruction and emulator disk latency; not a physical-drive measurement.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('fuse',type=Path)
    parser.add_argument('build',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=60)
    args=parser.parse_args()
    meta=json.loads((args.build/'build_metadata.json').read_text())
    results=[]
    for volume in meta['volumes']:
        result=measure(args.fuse.resolve(),(args.build/volume['trd_name']).resolve(),meta['player_labels'],args.timeout)
        assert result['frames']==volume['frames']
        results.append(result)
        print(json.dumps({key:value for key,value in result.items() if not isinstance(value,list)}),flush=True)
    args.output.write_text(json.dumps(results,indent=2))


if __name__=='__main__': main()
