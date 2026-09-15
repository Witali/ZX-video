"""Measure real Fuse 128K frame delivery and TR-DOS CALL duration separately."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from smoke_test_fuse import hidden_startupinfo
from validate_streaming_player import extract_file, parse_dir


def measure(fuse: Path, trd: Path, labels: dict, timeout: float, trdos_rom: Path | None = None) -> dict:
    image = trd.read_bytes()
    player = extract_file(image, next(e for e in parse_dir(image) if e[0] == 'PLAYER'))
    # Bracket ROM service: CALL 3D13h or direct-entry JP, through RAM return.
    call = 0x6000 + player.index(b'\xcd\x13\x3d', labels['read_n']-0x6000)
    events = [(labels['start'], 100), (labels['main_loop'], 101),
              (call, 102), (call+3, 103), (labels['finished'], 199)]
    events += [(labels[n], 198) for n in ('wait_packet_fill','stream_byte_fill','fatal') if n in labels]
    if 'frame_prepared' in labels: events.append((labels['frame_prepared'],107))
    if 'elapsed_fields' in labels: events.append((labels['clock_check'],108))
    if 'fast_read_enter' in labels: events.append((labels['fast_read_enter'],102))
    default_rom = fuse.parent/'roms/trdos.rom'
    if trdos_rom is None and default_rom.exists(): trdos_rom = default_rom
    rom_hash = hashlib.sha256(trdos_rom.read_bytes()).hexdigest() if trdos_rom else None
    if 'fast_read_enter' in labels and rom_hash != '91259fca6a8ded428cc24046f5b48b31d4043f2afbd9087d8946eaf4e10d71a5':
        raise ValueError('direct reader requires the tested TR-DOS 5.03 ROM; supply --trdos-rom')
    rom_args = ['--rom-beta128',str(trdos_rom.resolve())] if trdos_rom else []
    lines = ['base 10']
    for index, (address, event) in enumerate(events, 1):
        expression = (f'[{labels["elapsed_fields"]}] + 256 * [{labels["elapsed_fields"]+1}]' if event == 108 else
                      f'[{labels["field_counter"]}]' if event == 107 else 'spectrum:frames * 70908 + ula:tstates')
        lines += [f'breakpoint 0x{address:04x}', f'commands {index}',
                  f'print {event}', f'print {expression}']
        if event==198:lines += ['print 197','print z80:pc']
        lines += [
                  ('exit 77' if event == 199 else 'exit 99' if event == 198 else 'continue'), 'end']
    env = dict(os.environ, SDL_VIDEODRIVER='dummy')
    completed = subprocess.run([str(fuse), '--no-sound', '--no-autosave-settings',
        '--no-confirm-actions', '--speed', '1000', '--machine', '128', '--beta128',
        '--debugger-command', '\n'.join(lines), *rom_args, str(trd)], cwd=fuse.parent,
        env=env, capture_output=True, startupinfo=hidden_startupinfo(), timeout=timeout)
    if completed.returncode != 77:
        trace=(fuse.parent/'stdout.txt').read_text(errors='replace')
        raise RuntimeError(f'Fuse exit {completed.returncode}; trace tail: {trace[-300:]}')
    output = completed.stdout.decode(errors='replace')
    pattern = r'(?:0x[0-9a-fA-F]+|-?\d+)'
    if not any(re.fullmatch(pattern, line.strip()) for line in output.splitlines()):
        output = (fuse.parent/'stdout.txt').read_text(errors='replace')
    numbers = [int(line.strip(), 0) for line in output.splitlines() if re.fullmatch(pattern, line.strip())]
    if len(numbers) % 2: raise ValueError(f'incomplete Fuse trace: {output[-300:]}')
    frames = []; reads = []; read_start = None; decode_fields=[]; player_start=None; clock_checks=[]
    for event, timestamp in zip(numbers[::2], numbers[1::2]):
        if event == 100: player_start=timestamp
        elif event == 101: frames.append(timestamp)
        elif event == 107: decode_fields.append(timestamp)
        elif event == 108: clock_checks.append(timestamp)
        elif event == 102:
            if read_start is not None: raise ValueError('unpaired ROM entry')
            read_start = timestamp
        elif event == 103:
            if read_start is None: raise ValueError('unpaired ROM exit')
            reads.append(timestamp-read_start); read_start=None
    if len(frames) < 2 or not reads: raise ValueError(f'empty trace: {output[:300]}')
    if read_start is not None: raise ValueError('missing final ROM exit')
    if 'frame_prepared' in labels and len(decode_fields) != len(frames)-1:
        raise ValueError('incomplete CPU field trace')
    intervals = [b-a for a,b in zip(frames,frames[1:])]
    return dict(machine='Fuse 1.9.0 Spectrum 128 + Beta128', clock_hz=3546900,
                trdos_rom_sha256=rom_hash,
                player_startup_ms=(frames[0]-player_start)/3546.9 if player_start is not None else None,
                frames=len(frames), frame_interval_tstates=intervals,
                frame_interval_mean_ms=sum(intervals)/len(intervals)/3546.9,
                frame_interval_max_ms=max(intervals)/3546.9,
                measured_fps=3546900*len(intervals)/sum(intervals),
                decode_fields=decode_fields,
                clock_checks=clock_checks,
                rom_call_tstates=reads, rom_call_mean_ms=sum(reads)/len(reads)/3546.9,
                rom_call_max_ms=max(reads)/3546.9,
                note='ROM service intervals include entry CALL/JP, interrupts inside the interval and emulator disk latency; not a physical-drive measurement.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('fuse',type=Path)
    parser.add_argument('build',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=60)
    parser.add_argument('--trdos-rom',type=Path,help='default: roms/trdos.rom next to Fuse; direct reader verifies the ROM hash')
    args=parser.parse_args()
    meta=json.loads((args.build/'build_metadata.json').read_text())
    results=[]
    for volume in meta['volumes']:
        result=measure(args.fuse.resolve(),(args.build/volume['trd_name']).resolve(),meta['player_labels'],args.timeout,args.trdos_rom)
        assert result['frames']==volume['frames']
        results.append(result)
        print(json.dumps({key:value for key,value in result.items() if not isinstance(value,list)}),flush=True)
    args.output.write_text(json.dumps(results,indent=2))


if __name__=='__main__': main()
