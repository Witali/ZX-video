"""Record real Fuse audio plus paging latches, without per-pulse breakpoints.

FMF specification: https://sourceforge.net/p/fuse-emulator/wiki/FMF%20File%20Format/
Use the normal sound path at 100% speed. This complements, not replaces,
verify_pcm.py's complete PCM/bit/timing checks.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import re
import subprocess
import time
import wave
from pathlib import Path

import numpy as np
from verify_pcm import save
from smoke_test_fuse import hidden_startupinfo


def read_fmf(blob):
    """Decode the uncompressed standard-screen PCM-mono subset we request."""
    if blob[:8] != b'FMF_V1eU' or blob[9] != ord('$'):
        raise ValueError('expected little-endian uncompressed standard FMF')
    pos = 16
    frame = 0
    audio = bytearray()
    chunks = []
    timing_codes = set()
    ended = False

    def skip_rle(count):
        nonlocal pos
        written = 0
        while written < count:
            value = blob[pos]
            pos += 1
            written += 1
            if written < count and blob[pos] == value:
                written += 1 + blob[pos+1]
                pos += 2
        if written != count:
            raise ValueError('invalid FMF screen run')

    while pos < len(blob):
        tag = chr(blob[pos])
        if tag == '$':
            size = blob[pos+4]*int.from_bytes(blob[pos+5:pos+7], 'little')
            pos += 7
            skip_rle(size)
            skip_rle(size)
        elif tag == 'N':
            timing_codes.add(chr(blob[pos+3]))
            frame += blob[pos+1]
            pos += 4
        elif tag == 'S':
            rate = int.from_bytes(blob[pos+2:pos+4], 'little')
            if blob[pos+1] != ord('P') or blob[pos+4] != ord('M') or rate != 44100:
                raise ValueError('expected PCM16 mono 44100 Hz')
            count = int.from_bytes(blob[pos+5:pos+7], 'little') + 1
            pos += 7
            chunks.append((frame, len(audio)//2, count))
            audio.extend(blob[pos:pos+count*2])
            pos += count*2
        elif tag == 'X':
            pos += 1
            ended = True
        else:
            raise ValueError(f'unknown FMF block {tag!r} at {pos}')
    if pos != len(blob) or not ended or len(timing_codes) != 1:
        raise ValueError('incomplete or mixed-machine FMF')
    return np.frombuffer(audio, '<i2'), chunks, timing_codes.pop()


def summarize(movie, trace, meta, out):
    numbers = iter(int(s.strip(), 0) for s in trace.splitlines()
                   if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)', s.strip()))
    events = {100: [], 150: [], 200: []}
    widths = {100: 4, 150: 5, 200: 2}
    for tag in numbers:
        events[tag].append([next(numbers) for _ in range(widths[tag])])
    if len(events[100]) != 1 or len(events[200]) != 1 or len(events[150]) != 2*len(meta['sections']):
        raise ValueError('incomplete two-loop recording')
    raw, chunks, timing = read_fmf(movie)
    tstates = {'A': 69888, 'B': 70908, 'D': 71680}[timing]
    ready = events[100][0]
    chunk = next(c for c in chunks if c[0] == ready[0])
    start = chunk[1] + round(chunk[2]*ready[1]/tstates)
    pcm = raw[start:]
    with wave.open(str(out/'fuse-preview.wav'), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        wav.writeframes(pcm.tobytes())
    windows = []
    for offset in range(0, len(pcm)-22050+1, 22050):
        segment = pcm[offset:offset+22050].astype(float)/32768
        windows.append(dict(start_seconds=offset/44100, ac_rms=float(np.std(segment))))
    expected = [s['bank'] | 0x10 for s in meta['sections'][1:]+meta['sections'][:1]]*2
    actual = events[150]
    return dict(recording_complete=True, two_wraps_observed=True, timing_code=timing,
                startup_seconds=start/44100, recorded_playback_seconds=len(pcm)/44100,
                paging_latches_match=all(r[2] == r[3] == bank for r, bank in zip(actual, expected)),
                secondary_paging_unchanged=all(r[4] == ready[3] for r in actual),
                paging_events=actual, paging_event_fields=['frame', 'tstates', 'intended_value', '7ffd', '1ffd'],
                half_second_windows=windows,
                all_half_second_windows_have_signal=bool(windows) and all(w['ac_rms'] > 1e-6 for w in windows),
                scope='Fuse sound generator capture, not physical sound-card loopback; sparse trace is not an all-bit check')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--fuse', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--machine', choices=('128', 'scorpion', 'auto'), default='128')
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        p.error('output must be empty')
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((args.input/'player.json').read_bytes())
    labels = meta['player_labels']
    lines = ['base 10', 'set $wraps 0']
    event_id = 0

    def event(address, tag, expressions, after=(), condition='', stop=False):
        nonlocal event_id
        event_id += 1
        lines.extend([f'breakpoint {address}', f'commands {event_id}', f'print {tag}'])
        lines.extend('print '+x for x in expressions)
        lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue', 'end'])
        if condition:
            lines.append(f'condition {event_id} {condition}')

    event(labels['ready'], 100, ['spectrum:frames', 'ula:tstates', 'ula:mem7ffd', 'ula:mem1ffd'])
    for i in range(len(meta['sections'])):
        event(labels[f'page_{i}']+2, 150, ['spectrum:frames', 'ula:tstates',
              'z80:'+meta.get('paging_value_register', 'a'), 'ula:mem7ffd', 'ula:mem1ffd'],
              ['set $wraps $wraps+1'] if i == len(meta['sections'])-1 else [])
    event(labels['out_0_0_0']+(4 if meta.get('steady', False) else 3), 200,
          ['spectrum:frames', 'ula:tstates'], condition='$wraps==2', stop=True)
    script = '\n'.join(lines)
    (out/'fuse-debugger.txt').write_text(script, encoding='utf-8', newline='\n')
    movie_path = out/'capture.fmf'
    command = [str(args.fuse.resolve()), '--sound', '--sound-freq', '44100',
               '--no-autosave-settings', '--no-confirm-actions', '--speed', '100',
               '--movie-start', str(movie_path), '--movie-compr', 'None', '--debugger-command', script]
    if args.machine != 'auto':
        command.extend(['--machine', args.machine, '--beta128'])
    command.append(str((args.input/'audiobook-preview.trd').resolve()))
    start = time.monotonic()
    result = subprocess.run(command, cwd=args.fuse.parent, capture_output=True,
                            startupinfo=hidden_startupinfo(), timeout=120)
    (out/'fuse-trace.txt.gz').write_bytes(gzip.compress(result.stdout, mtime=0))
    (out/'fuse-stderr.txt').write_bytes(result.stderr)
    if result.returncode != 77:
        raise ValueError(f'Fuse did not finish the recording: {result.returncode}')
    movie = movie_path.read_bytes()
    (out/'capture.fmf.gz').write_bytes(gzip.compress(movie, mtime=0))
    report = summarize(movie, result.stdout.decode(errors='replace'), meta, out)
    report.update(date='2026-10-02', requested_machine=args.machine, elapsed_seconds=time.monotonic()-start,
                  source_trd_sha256=hashlib.sha256((args.input/'audiobook-preview.trd').read_bytes()).hexdigest(),
                  fuse_sha256=hashlib.sha256(args.fuse.read_bytes()).hexdigest(),
                  recorder_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest())
    movie_path.unlink()  # Only our just-created uncompressed capture; gzip is retained.
    save(out/'report.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('paging_events', 'half_second_windows')}))


if __name__ == '__main__':
    main()
