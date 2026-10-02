"""Measure guarded IMA/PDM microkernels, without changing the release player.

The complete existing stream is tested in independent <=128-byte blocks.
This covers its arithmetic and PDM bits, NOT continuous playback, ULA delays,
bank/page tails, cold boot, disk I/O, sample cadence or audible quality.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, deque
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

from ima_codec import INDEX, STEPS, decode, transition

HERE = Path(__file__).resolve().parent
CLOCK = 3546900
ORIGIN, TABLE, INPUT = 0x8000, 0xA000, 0xC000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit(packed, predictor, index):
    if not packed:
        raise ValueError('cannot authorize an empty stream')
    minimum, maximum, clips = float('inf'), float('-inf'), 0
    for byte in packed:
        for code in (byte & 15, byte >> 4):
            step = STEPS[index]
            delta = ((step >> 3) + (step if code & 4 else 0)
                     + (step >> 1 if code & 2 else 0)
                     + (step >> 2 if code & 1 else 0))
            raw = predictor + (-delta if code & 8 else delta)
            clips += int(not -32768 <= raw <= 32767)
            minimum, maximum = min(minimum, raw), max(maximum, raw)
            predictor, index = transition(predictor, index, code)
    return dict(samples=2 * len(packed), saturation_events=clips,
                raw_predictor_min=minimum, raw_predictor_max=maximum)


def clean_table():
    data = bytearray()
    for index, step in enumerate(STEPS):
        for code in range(16):
            delta = ((step >> 3) + (step if code & 4 else 0)
                     + (step >> 1 if code & 2 else 0)
                     + (step >> 2 if code & 1 else 0))
            if code & 8:
                delta = -delta
            nxt = max(0, min(88, index + INDEX[code & 7]))
            data.extend(struct.pack('<HH', delta & 65535, TABLE + 64 * nxt))
    return data


def assemble(work, slots, balanced):
    work.mkdir(parents=True, exist_ok=True)
    (work / 'config.inc').write_text(
        f'slots: EQU {slots}\nbalanced: EQU {int(balanced)}\n', encoding='ascii')
    source = (HERE / 'ima-rate-probe.asm').read_text(encoding='utf-8')
    (work / 'probe.asm').write_text(source, encoding='utf-8', newline='\n')
    command = [sys.executable, '-m', 'pyz80.pyz80', '--obj=probe.bin',
               '--lstfile=probe.lst', '-s', '.*', 'probe.asm']
    result = subprocess.run(command, cwd=work, capture_output=True, text=True, check=True)
    symbols = next(ast.literal_eval(line) for line in result.stdout.splitlines()
                   if line.startswith('{'))
    blob = (work / 'probe.bin').read_bytes()
    return blob, symbols


def holds(slots, balanced, high):
    # OUT-to-OUT, including one saved-A pulse. Instruction totals are listed
    # in the ASM. Extra slots are placed before the final sample publication.
    return [58, 60, 56, 50, 55, 52 if balanced else 32,
            56 if balanced else (46 if high else 32),
            *([32] * (slots - 8)), 50]


def measure(blob, labels, packed, initial_predictor, initial_index, slots, balanced):
    from z80 import Z80Machine

    pcm, indices = decode(packed, initial_predictor, initial_index)
    expected_intervals = holds(slots, balanced, False) + holds(slots, balanced, True)
    histogram = Counter()
    total_bits = total_samples = blocks = 0
    # The entire real payload, including bytes adjacent to real bank/page
    # boundaries, is decoded; those boundaries are NOT executed in this probe.
    for start in range(0, len(packed), 128):
        part = packed[start:start + 128]
        count = len(part) * 2
        predictor = initial_predictor if start == 0 else int(pcm[2 * start - 1])
        index = initial_index if start == 0 else int(indices[2 * start - 1])
        wanted = pcm[2 * start:2 * start + count]
        wanted_indices = indices[2 * start:2 * start + count]
        levels = [((predictor + 32768) >> 8)] + [((int(p) + 32768) >> 8) for p in wanted]
        machine = Z80Machine()
        machine.memory[:] = b'\xa5' * 65536
        machine.set_memory_block(ORIGIN, blob)
        machine.set_memory_block(TABLE, clean_table())
        machine.set_memory_block(INPUT, part)
        machine.pc = labels['low']
        machine.hl = INPUT
        machine.alt_hl = TABLE + 64 * index
        machine.ix = predictor + 32768
        machine.bc = 0x10fe
        machine.d, machine.e, machine.a = levels[0], 0, 128
        budget = 1000000
        machine.ticks_to_stop = budget
        before = bytes(machine.memory)
        times = []
        error = 128
        pending = deque([0, 0, 0])
        checked_samples = 0

        def output(port, value):
            nonlocal error, checked_samples
            n = len(times)
            sample = n // slots
            if port != 0x10fe or value & 15 or machine.d != levels[sample]:
                raise AssertionError(f'PCM/port/border mismatch at block {start}, slot {n}')
            error += levels[sample]
            bit = pending.popleft()
            pending.append(int(error >= 256))
            error &= 255
            if ((value >> 4) & 1) != bit:
                raise AssertionError('PDM bit mismatch')
            if n % slots == slots - 1:
                if (machine.ix != int(wanted[sample]) + 32768
                        or machine.alt_hl != TABLE + 64 * int(wanted_indices[sample])):
                    raise AssertionError(f'IMA predictor/index mismatch at {2 * start + sample}')
                checked_samples += 1
            times.append(budget - machine.ticks_to_stop)
            if len(times) == slots * count + 1:
                machine.set_breakpoint(labels['low_out0'] + 2)

        machine.set_output_callback(output)
        while len(times) < slots * count + 1 or machine.pc != labels['low_out0'] + 2:
            if machine.run() & machine._TICKS_LIMIT_HIT:
                raise AssertionError('probe did not finish')
        actual = [b - a for a, b in zip(times, times[1:])]
        expected = expected_intervals * len(part)
        if actual != expected:
            raise AssertionError(f'T-state mismatch: {actual[:2 * slots]} vs {expected[:2 * slots]}')
        if bytes(machine.memory) != before or checked_samples != count:
            raise AssertionError('memory or sample count mismatch')
        histogram.update(actual)
        total_bits += len(times)
        total_samples += checked_samples
        blocks += 1
    mean = sum(expected_intervals) / 2
    return dict(slots_per_sample=slots,balanced=balanced,code_bytes=len(blob),
                binary_sha256=sha(blob),independent_blocks=blocks,
                samples_verified=total_samples,pdm_bits_verified=total_bits,
                every_predictor_index_pcm8_and_bit_exact=True,memory_unchanged=True,
                low_tstates=sum(holds(slots, balanced, False)),
                high_tstates=sum(holds(slots, balanced, True)),mean_tstates=mean,
                delta_from_current_438_tstates=mean-438,
                native_pcm_rate_hz=CLOCK/mean,native_pdm_rate_hz=CLOCK*slots/mean,
                budget_left_at_8000_hz_tstates=CLOCK/8000-mean,
                maximum_native_hold_tstates=max(histogram),
                interval_histogram_tstates=dict(sorted(histogram.items())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=HERE.parent / '.tmp' / 'ima-rate-probe')
    parser.add_argument('--report', type=Path, default=HERE / 'ima-rate-probe.json')
    args = parser.parse_args()
    baseline = HERE / 'ima-preview'
    meta = json.loads((baseline / 'player.json').read_bytes())
    packed = gzip.decompress((baseline / 'soundtrack.ima.gz').read_bytes())
    guard = audit(packed, meta['initial_predictor'], meta['initial_index'])
    if guard['saturation_events']:
        raise ValueError('stream cannot use the no-saturation fast path')
    guard_checks = dict(positive=audit(bytes([7]), 32760, 0),
                        negative=audit(bytes([143]), -32761, 0))
    if any(check['saturation_events'] != 2 for check in guard_checks.values()):
        raise AssertionError('guard failed to detect a deliberately unsafe stream')
    variants = {}
    for slots, balanced in ((8, False), (8, True), (9, False), (10, False)):
        name = f'{slots}-' + ('balanced' if balanced else 'unpadded')
        blob, labels = assemble(args.work.resolve() / name, slots, balanced)
        variants[name] = measure(blob, labels, packed, meta['initial_predictor'],
                                 meta['initial_index'], slots, balanced)
        print(name, json.dumps(variants[name]), flush=True)
    release = (HERE.parent / 'ZX-audiobook-IMA-ADPCM-test.trd').read_bytes()
    baseline_verification = json.loads((baseline / 'verification.json').read_bytes())
    if sha(release) != baseline_verification['fuse']['trd_sha256']:
        raise AssertionError('release image is no longer the verified baseline')
    report = dict(date='2026-10-02',scope='CPU-only feasibility; not a release',
                  release=False,full_player_verified=False,
                  packed_sha256=sha(packed),release_trd_sha256=sha(release),
                  probe_asm_sha256_lf=sha((HERE / 'ima-rate-probe.asm').read_text().encode()),
                  initial_predictor=meta['initial_predictor'],initial_index=meta['initial_index'],
                  guard=guard,unsafe_stream_guard_checks=guard_checks,
                  baseline_fuse=baseline_verification['fuse'],variants=variants,
                  instruction_timing_reference='https://www.zilog.com/docs/z80/um0080.pdf',
                  excluded=['ULA contention','page/bank tails','continuous loop',
                            'TR-DOS and cold boot','listening and noise measurements'],
                  decision='8 slots is the next practical target; 9 needs tighter timing and tails; '
                           '10 already exceeds the 8 kHz CPU budget in this kernel. '
                           'Keep the verified release image unchanged.')
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
