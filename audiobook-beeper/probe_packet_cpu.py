"""Assemble/execute a packet codebook microkernel, not a bootable player.

Every source sample is covered in independent <=512-byte input blocks.
There are no live paging, refill, ULA or loop-tail claims. All data is
read-only during each run. Python prepares data only; ASM emits opcodes.
"""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np
from z80 import Z80Machine

from ima_codec import decode, decoder_table, require_unclipped
from probe_feedback_packets import integral_table

HERE = Path(__file__).resolve().parent
FIRST, STRIDE0, SECOND, STRIDE1 = 0x8000, 40, 0xa800, 64
HOLDS0 = [36,28,28,31,27,23,23,16]
HOLDS1 = [31,23,27,28,33,30,35,31]


def integer_step(pcm8, state):
    q = (state // 2 - 8) * 8192
    recent = (2 * (state % 2) - 1) * 32768
    x = ((pcm8 // 4) * 4 + 2) * 256
    word = 0
    for _ in range(16):
        u = x + q + recent // 2
        bit = int(u >= 32768)
        recent = u - bit * 65536
        q += x - bit * 65536
        word = word * 2 + bit
    assert q % 8192 == 0
    return word, max(0, min(15, q // 8192 + 8)) * 2 + int(recent >= 0)


def assemble(out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'probe.asm').write_bytes((HERE / 'ima-packet-probe.asm').read_bytes())
    (out / 'config.inc').write_text('second_high: EQU 0x5800\npcm_low: EQU 0x5A00\n')
    run = subprocess.run([sys.executable, '-m', 'pyz80.pyz80', '--obj=probe.bin',
                          '--lstfile=probe.lst', '-s', '.*', 'probe.asm'], cwd=out,
                         capture_output=True, text=True)
    (out / 'assembler.log').write_text(run.stdout + run.stderr)
    if run.returncode:
        raise RuntimeError(run.stdout + run.stderr)
    labels = next(ast.literal_eval(s) for s in run.stdout.splitlines() if s.startswith('{'))
    blob = (out / 'probe.bin').read_bytes()
    # pyz80 omits the final three unreferenced DS padding bytes from --obj.
    assert labels['code_end'] == 0xe800 and len(blob) == 26621
    return blob


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--packed', type=Path)
    args = p.parse_args()
    blob = assemble(args.output / 'assembly')
    packed = gzip.decompress((args.packed or (HERE / 'experiments/ima-feedback64/soundtrack.ima.gz')).read_bytes())
    guard = require_unclipped(packed)
    pcm, indices = decode(packed + b'\0')
    levels = ((pcm.astype(np.int32) + 32768) >> 8).astype('u1')
    words, successors, _ = integral_table(64, 2)
    table = bytearray()
    for value in range(64):
        for state in range(32):
            word, nxt = integer_step(value * 4, state)
            assert (word, nxt) == (int(words[value, state]), int(successors[value, state]))
            table += struct.pack('<HBB', FIRST + (word >> 8) * STRIDE0, nxt * 4, word & 255)
    expected_words = []
    states = [16]
    for value in levels:
        word, state = integer_step(int(value), states[-1])
        expected_words.append(word)
        states.append(state)
    expected = np.unpackbits(np.array(expected_words, dtype='>u2').view('u1'))
    counts = dict(blocks=0, samples=0, outputs=0)
    emitted = bytearray()
    for start in range(0, len(packed), 512):
        nbytes = min(512, len(packed) - start)
        n = 2 * nbytes
        base = 2 * start
        m = Z80Machine()
        m.memory[:] = b'\xa5' * 65536
        m.set_memory_block(FIRST, blob)
        m.set_memory_block(0x4000, decoder_table(0x4000, False))
        m.set_memory_block(0x6000, table)
        m.set_memory_block(0x5800, bytes((SECOND + x * STRIDE1) >> 8 for x in range(256)))
        m.set_memory_block(0x5900, bytes((SECOND + x * STRIDE1) & 255 for x in range(256)))
        m.set_memory_block(0x5a00, bytes((x & 4) << 5 for x in range(256)))
        m.set_memory_block(0x5b00, bytes(0x60 + (x >> 3) for x in range(256)))
        m.set_memory_block(0xf000, (packed + b'\0\0')[start:start+nbytes+2])
        first = expected_words[base]
        m.pc = FIRST + (first >> 8) * STRIDE0
        m.b, m.c, m.d, m.e = first & 255, 254, 16, states[base+1] * 4
        m.a = (packed[start] >> 4) * 4
        m.alt_af = 1
        m.iy = 0xf001
        m.ix = int(pcm[base]) + 32768
        m.alt_hl = 0x4000 + int(indices[base]) * 64
        before = bytes(m.memory)
        times, values = [], []
        budget = 2000000
        def output(port, value):
            offset = len(values)
            assert port & 255 == 254 and value in (0, 16), (offset, port, value)
            sample = offset // 16
            if offset % 16 == 4 and sample < n:
                assert m.ix == int(pcm[base+sample+1]) + 32768, (base, offset, 'predictor')
                assert m.alt_hl == 0x4000 + int(indices[base+sample+1]) * 64
            values.append(value >> 4)
            times.append(budget - m.ticks_to_stop)
            if len(values) == 16*n+1:
                m.set_breakpoint(m.pc)
        m.set_output_callback(output)
        m.ticks_to_stop = budget
        while len(values) < 16*n+1:
            if m.run() & m._TICKS_LIMIT_HIT:
                raise AssertionError('native probe timeout')
        assert np.array_equal(values, expected[16*base:16*(base+n)+1]), (base, 'bits')
        wanted = np.tile(HOLDS0 + HOLDS1 + HOLDS0 + HOLDS1[:-1] + [41], nbytes)
        actual = np.diff(times)
        assert np.array_equal(actual, wanted), (base, actual[:32].tolist(), wanted[:32].tolist())
        assert bytes(m.memory) == before, 'unexpected native write'
        emitted.extend(values[:-1])
        counts['blocks'] += 1
        counts['samples'] += n
        counts['outputs'] += len(values)
    report = dict(scope=__doc__, complete_microkernel=True, full_player_verified=False,
                  guard=guard, **counts, every_bit_exact=True, every_predictor_and_index_exact=True,
                  read_only_memory_verified=True, table_integer_cases=2048,
                  code_bytes=len(blob), table_bytes=len(table),
                  native_low_tstates=450, native_high_tstates=460, native_mean_tstates=455,
                  baseline_mean_tstates=433.25, delta_tstates=21.75,
                  pulses_per_sample=16, native_pdm_rate_hz=3546900*16/455,
                  native_pcm_rate_hz=3546900/455,
                  holds_low=HOLDS0+HOLDS1, holds_high=HOLDS0+HOLDS1[:-1]+[41],
                  packed_sha256=hashlib.sha256(packed).hexdigest(),
                  binary_sha256=hashlib.sha256(blob).hexdigest(),
                  bitstream_sha256=hashlib.sha256(emitted).hexdigest())
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
