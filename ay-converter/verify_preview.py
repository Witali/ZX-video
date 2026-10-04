"""Verify every register and the complete resident preview in native Z80 and Fuse."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from music_player import BANKS, BANK_BYTES, ORIGIN
from support import hidden_startupinfo


def expected_registers(packed):
    output = bytearray()
    if len(packed) % 9:
        raise ValueError('truncated AY9 stream')
    for i in range(0, len(packed), 9):
        row = packed[i:i+9]
        noise = (row[1] >> 4) | (row[3] & 16)
        output.extend((row[0], row[1] & 15, row[2], row[3] & 15,
                       row[4], row[5] & 15, noise, 0x2a if noise else 0x38,
                       *row[6:9]))
    return bytes(output)


def extract_player(disk):
    for i in range(128):
        entry = disk[i*16:i*16+16]
        if entry[:8] == b'PLAYER  ':
            start = (entry[15]*16 + entry[14])*256
            return disk[start:start+int.from_bytes(entry[11:13], 'little')]
    raise ValueError('PLAYER.C missing')


def native_check(code, metadata, expected):
    from z80 import Z80Machine
    m = Z80Machine()
    m.memory[:] = b'\xa5' * 65536
    m.set_memory_block(ORIGIN, code)
    labels = metadata['player_labels']
    banks = metadata.get('memory', {}).get('data_banks', BANKS)
    looping = metadata.get('loop_playback', False)
    cycles = 2 if looping else 1
    writes, pages = [], []
    selected = 0
    def output(port, value):
        nonlocal selected
        if port == 0x7ffd:
            bank = value & 7
            if bank not in banks:
                raise AssertionError('invalid bank')
            pages.append(bank)
            first = list(banks).index(bank)*BANK_BYTES
            payload = expected[first:first+BANK_BYTES]
            m.set_memory_block(0xc000, payload + b'\xa5'*(16384-len(payload)))
        elif port == 0xfffd:
            selected = value
        elif port == 0xbffd:
            writes.append((selected, value))
        else:
            raise AssertionError(f'unexpected runtime port: {port:04x}')
    m.set_output_callback(output)
    output(0x7ffd, 0x10)
    m.hl, m.sp = 0xc000, 0xb800
    histogram = Counter()
    m.set_breakpoint(labels['wait_field'])
    for tick in range(metadata['ticks']*cycles):
        m.pc = labels['field_start']
        m.ticks_to_stop = 10000
        while m.pc != labels['wait_field']:
            if m.run() & m._TICKS_LIMIT_HIT:
                raise AssertionError('tick failed to finish')
        elapsed = 10000-m.ticks_to_stop
        histogram[elapsed] += 1
        index = tick % metadata['ticks']
        want = list(enumerate(expected[index*11:(index+1)*11]))
        if writes[-11:] != want or len(writes) != (tick+1)*11:
            raise AssertionError(f'wrong register sequence at tick {tick}')
        if m.sp != 0xb800:
            raise AssertionError('stack leak')
    if looping:
        return dict(complete=True, ticks=metadata['ticks']*cycles, cycles_verified=cycles,
                    register_writes=len(writes), registers_exact=True, bank_sequence=pages,
                    eof_mutes=False, seamless_loop=True,
                    deterministic_field_work_tstates=dict(sorted(histogram.items())),
                    scope='independent Z80 core; no ULA, IRQ, HALT or disk latency')
    m.clear_breakpoint(labels['wait_field'])
    m.set_breakpoint(labels['finished_wait'])
    m.pc = labels['field_start']; m.ticks_to_stop = 10000
    while m.pc != labels['finished_wait']:
        if m.run() & m._TICKS_LIMIT_HIT:
            raise AssertionError('missing EOF')
    if writes[-3:] != [(8, 0), (9, 0), (10, 0)]:
        raise AssertionError('EOF must mute all channels')
    return dict(complete=True, ticks=metadata['ticks'], register_writes=metadata['ticks']*11,
                registers_exact=True, bank_sequence=pages, eof_mutes=True,
                deterministic_field_work_tstates=dict(sorted(histogram.items())),
                scope='independent Z80 core; no ULA, IRQ, HALT or disk latency')


def fuse_check(fuse, directory, metadata, expected, record=False):
    labels = metadata['player_labels']
    trace_dir = directory / 'verification-work'
    trace_dir.mkdir(exist_ok=True)
    cycles = 2 if metadata.get('loop_playback') else 1
    total_ticks = metadata['ticks']*cycles
    expected = expected*cycles
    disk_path = directory/metadata.get('disk_filename', 'audiobook-preview.trd')
    lines, events = ['base 10', 'set $r 0', 'set $ticks 0'], []
    loading_addresses = [0x4000+plane*256+i for plane in range(8) for i in range(96)] if metadata.get('loading_message') else []
    # Check pixels independently of the producer: the whole message area must
    # exist before the first payload read and be blank before playback.
    pixels = [f'[{address}]' for address in loading_addresses]
    stamp = 'spectrum:frames*70908+ula:tstates'
    def event(label, tag, expressions, after=(), stop=False, condition=None):
        events.append((tag, len(expressions)))
        lines.extend([f'breakpoint {label}', f'commands {len(events)}', f'print {tag}'])
        lines.extend(f'print {expr}' for expr in expressions)
        lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue', 'end'])
        if condition:
            lines.append(f'condition {len(events)} {condition}')
    event(labels['ready'], 100, [stamp], ['set $r 1'])
    if loading_addresses:
        lines.append('set $loadseen 0')
        event(labels['disk_call'], 103, [stamp, *pixels], ['set $loadseen 1'], condition='$loadseen==0')
        event(labels['ready'], 104, [stamp, *pixels])
    event(labels['ay_out']+2, 140, [stamp, 'z80:d', 'z80:e'])
    event(labels['tick_end'], 143, [stamp], ['set $ticks $ticks+1'])
    event(labels['disk_call'], 102, [stamp, '$r'])
    if metadata.get('loop_playback'):
        event(labels['field_start'], 200, [stamp], stop=True, condition=f'$ticks=={total_ticks}')
    else:
        event(labels['finished_wait'], 200, [stamp], stop=True)
    script = '\n'.join(lines)
    (trace_dir / 'fuse-debugger.txt').write_text(script, encoding='utf-8')
    command = [str(fuse.resolve()), '--sound' if record else '--no-sound',
               '--no-autosave-settings', '--no-confirm-actions', '--speed', '100' if record else '10000',
               '--machine', '128', '--beta128', '--debugger-command', script]
    if record:
        command += ['--sound-freq', '44100', '--movie-start', str((trace_dir/'capture.fmf').resolve()),
                    '--movie-compr', 'None']
    command.append(str(disk_path.resolve()))
    epoch = time.time()
    result = subprocess.run(command, cwd=fuse.parent, capture_output=True,
                            env=dict(os.environ, SDL_VIDEODRIVER='dummy'),
                            startupinfo=hidden_startupinfo(), timeout=max(180, total_ticks/50+120))
    trace = result.stdout.decode(errors='replace')
    fallback = fuse.parent / 'stdout.txt'
    if not re.search(r'^\s*\d+\s*$', trace, re.M) and fallback.exists() and fallback.stat().st_mtime >= epoch-2:
        trace = fallback.read_text(errors='replace')
    (trace_dir / 'fuse-trace.txt.gz').write_bytes(gzip.compress(trace.encode(), mtime=0))
    (trace_dir / 'fuse-stderr.txt').write_bytes(result.stderr)
    if result.returncode != 77:
        raise AssertionError(f'Fuse did not finish: {result.returncode}')
    numbers = [int(s.strip(), 0) for s in trace.splitlines()
               if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)', s.strip())]
    widths = dict(events)
    pos = 0; writes = []; ticks = []; reads = []; boot = []; ends = []; before_load = []; after_load = []
    while pos < len(numbers):
        tag = numbers[pos]; pos += 1
        count = widths[tag]
        row = numbers[pos:pos+count]; pos += count
        {100:boot, 140:writes, 143:ticks, 102:reads, 200:ends, 103:before_load, 104:after_load}[tag].append(row)
    if len(boot) != 1 or len(ends) != 1 or len(ticks) != total_ticks:
        raise AssertionError('incomplete Fuse playback')
    if len(writes) != len(expected) or any(r[1] for r in reads):
        raise AssertionError('missing writes or runtime disk access')
    for i, (_, register, value) in enumerate(writes):
        if register != i % 11 or value != expected[i]:
            raise AssertionError(f'Fuse register mismatch at byte {i}')
    starts = [writes[i][0] for i in range(0, len(writes), 11)]
    fields = [x//70908 for x in starts]
    missing = [i for i in range(1, len(fields)) if fields[i] != fields[0]+i]
    if missing:
        raise AssertionError(f'AY field deadlines missed: {missing[:10]}')
    if ends[0][0]//70908 != fields[-1]+1:
        raise AssertionError('last tick not held for one full field')
    phases = [x % 70908 for x in starts]
    loading = None
    if loading_addresses:
        assert len(before_load) == len(after_load) == 1
        assert any(before_load[0][1:]) and not any(after_load[0][1:])
        assert before_load[0][0] <= reads[0][0] < after_load[0][0]
        loading = dict(shown_before_payload_reads=True, hidden_before_playback=True,
                       bitmap_bytes_verified=len(loading_addresses))
    recording = None
    if record:
        # The complete FMF parser is included with this standalone converter.
        from fmf_audio import read_fmf
        import wave
        movie = (trace_dir/'capture.fmf').read_bytes()
        audio, chunks, timing = read_fmf(movie)
        assert timing == 'B', 'expected Spectrum 128 timing'
        frame, phase = divmod(starts[0], 70908)
        chunk = next(c for c in chunks if c[0] == frame)
        start = chunk[1]+round(chunk[2]*phase/70908)
        pcm = audio[start:]
        with wave.open(str(directory/'fuse-preview.wav'), 'wb') as wav:
            wav.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
            wav.writeframes(pcm.tobytes())
        (trace_dir/'capture.fmf.gz').write_bytes(gzip.compress(movie, mtime=0))
        (trace_dir/'capture.fmf').unlink()
        recording = dict(complete=True, source='normal-speed Fuse sound generator',
                         startup_seconds=start/44100, duration_seconds=len(pcm)/44100,
                         cycles=cycles, output='fuse-preview.wav', sample_rate_hz=44100,
                         physical_sound_card_recording=False)
    return dict(complete=True, cold_boot=True, ticks=len(ticks), register_writes=len(writes),
                cycles_verified=cycles, recording=recording, loading_message=loading,
                every_register_exact=True, missing_or_duplicate_fields=missing,
                runtime_disk_reads=0, startup_sector_reads=len(reads),
                first_out_phase_min_tstates=min(phases), first_out_phase_max_tstates=max(phases),
                first_out_interval_min_tstates=min(b-a for a,b in zip(starts, starts[1:])) if len(starts)>1 else None,
                first_out_interval_max_tstates=max(b-a for a,b in zip(starts, starts[1:])) if len(starts)>1 else None,
                first_out_to_eof_tstates=ends[0][0]-starts[0],
                trd_sha256=hashlib.sha256(disk_path.read_bytes()).hexdigest(),
                fuse_sha256=hashlib.sha256(fuse.read_bytes()).hexdigest(),
                hardware_tested=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--fuse', type=Path, required=True)
    p.add_argument('--record', action='store_true', help='also capture normal-speed Fuse sound')
    args = p.parse_args()
    metadata = json.loads((args.directory/'player.json').read_bytes())
    packed = gzip.decompress((args.directory/'soundtrack.ay9.gz').read_bytes())
    expected = expected_registers(packed)
    if hashlib.sha256(expected).hexdigest() != metadata['registers_sha256']:
        raise AssertionError('prepared audio identity changed')
    code = extract_player((args.directory/metadata.get('disk_filename', 'audiobook-preview.trd')).read_bytes())
    native = native_check(code, metadata, expected)
    print(json.dumps(native), flush=True)
    fuse = fuse_check(args.fuse, args.directory, metadata, expected, record=args.record)
    sources = [Path(__file__).with_name(name) for name in
               ('verify_preview.py', 'music_player.py', 'ay-player.asm',
                'trd.py', 'support.py', 'fmf_audio.py')]
    report = dict(complete=True, native=native, fuse=fuse,
                  verification_sources_sha256_lf={path.name:hashlib.sha256(
                      path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for path in sources})
    (args.directory/'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    summary_path = args.directory/'report.json'
    summary = json.loads(summary_path.read_bytes())
    summary['disk_timing_verified'] = True
    summary['verification'] = 'verification.json'
    names = [*summary['artifacts'], 'verification.json', 'verification-work/fuse-trace.txt.gz']
    if args.record:
        names += ['fuse-preview.wav', 'verification-work/capture.fmf.gz']
    for name in dict.fromkeys(names):
        path = args.directory/name
        summary['artifacts'][name] = dict(bytes=path.stat().st_size,
                                         sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(fuse), flush=True)


if __name__ == '__main__':
    main()
