import json
from pathlib import Path
import struct
import unittest

import numpy as np

from benchmark_causal_tiles import Harness
import causal_tile_z80 as machine
from probe_hybrid_tiles import Writer, OFFSETS, encode, decode, read_header, read_group
from probe_motion_entropy import Reader
from probe_motion_metadata import transform
from test_causal_tiles import predict
import test_causal_tiles as causal_tests


def header(count):
    alphabet = bytes([0, 2, 1, 3, 1, 2, 0, 3, 2, 3, 1, 0, 3, 2, 1, 0])
    return b'FPR1'+alphabet+b'FMO1\x08FMR1\x08'+bytes([81])+struct.pack('<I', count)+b''.join(struct.pack('<bb', *xy) for xy in OFFSETS)


def run_z80(data, expected):
    r = Reader(data)
    _, remaining, offsets, mapping, tables = read_header(r)
    h = Harness(tables, mapping, offsets, skip_empty=True, hybrid=True)
    rows, start = [], 0
    while remaining:
        n, _, bits, v, bm, at, encoded = read_group(r, remaining)
        h.begin(encoded, v, bm, at)
        for i in range(n):
            rows.append(h.run(i, expected[start+i].tobytes()))
        assert h.position() == bits
        start += n; remaining -= n
    r.end()
    return rows


class HybridTileTests(unittest.TestCase):
    def test_baseline_code_unchanged(self):
        # Header contains the real 17-context tables; only their context count
        # affects code generation. Compare bytes as well as instruction timing.
        root = Path(__file__).parent
        for option, name in ((False, 'causal_tiles_cpu_measurements.json'), (True, 'causal_tiles_skip_empty_cpu_measurements.json')):
            report = json.loads((root/name).read_text(encoding='utf-8'))
            # Prefix layout expects real short/long tables. Recover them from
            # the existing profiling report, avoiding untracked fixture files.
            profile = json.loads((root/'direct_values_profile.json').read_text(encoding='utf-8'))
            model = next(row for row in profile['rows'] if row['name'] == 'direct')
            group = next(row for row in model['groups'] if row['bitmap_contexts'] == 16)
            code, labels, listing, _ = machine.build([bytes(t) for t in group['tables']], group['context_map'], OFFSETS, skip_empty=option)
            self.assertEqual(code.hex(), report['code_hex'])
            self.assertEqual(labels, report['labels'])
            self.assertEqual(listing, report['instruction_listing'])

    def test_causal_modes_edges_and_adaptive_groups(self):
        rng = np.random.default_rng(8216)
        states, residual, vectors = [], [], []
        previous = bytes(3840)
        for i in range(9):
            v = bytes((tile+i*17) % 82 for tile in range(192))
            predicted = np.frombuffer(predict(previous, v), dtype=np.uint8)
            target = predicted.copy()
            positions = np.arange(3840) if i % 3 == 0 else np.arange(i, 3840, 31)
            target[positions] ^= rng.integers(1, 256, size=len(positions), dtype=np.uint8)
            states.append(target); residual.append(target ^ predicted); vectors.append(list(v))
            previous = target.tobytes()
        states, residual, vectors = (np.asarray(v, dtype=np.uint8) for v in (states, residual, vectors))
        for threshold in (None, 128, 64, 0):
            with self.subTest(threshold=threshold):
                data, detail = encode(header(9), states, vectors, residual, bytes(256), [bytes([8]*256)]*2, threshold, cap=4500)
                actual, rows = decode(data)
                self.assertEqual(actual, states.tobytes())
                self.assertEqual(rows, detail['frames'])
                self.assertGreater(len(detail['groups']), 1)
                measured = run_z80(data, states)
                for want, got in zip(rows, measured):
                    self.assertEqual({k: got[k] for k in ('bits', 'values', 'literals', 'cache')}, {k: want[k] for k in ('bits', 'values', 'literals', 'cache')})
                for bad in (data[:-1], data+b'!', b'bad!'+data[4:]):
                    with self.assertRaises(ValueError):
                        decode(bad)

    def mixed(self):
        # Three frames cross Huffman/raw alignment and retain history; one
        # literal follows a single-bit code, another starts byte-aligned.
        table = bytes([1]+[0]*254+[1])
        v, bm, at, writer = bytearray(3*192), bytearray(3*384), bytearray(3*96), Writer()
        v[1] = 82; v[2] = 82; bm[0] = 128
        writer.put(1, 1); writer.literal(bytes([255]*16)); writer.literal(bytes(16))
        at[0] = 128; writer.put(1, 1)
        # Next frame: a Huffman correction to zero, proving raw-copy C state.
        bm[384] = 128; writer.put(0, 1)
        at[96] = 128; writer.put(1, 1)
        v[2*192] = 80  # Cache resumes after two frames of literal/in-place work.
        vb, mb = transform(bytes(v), 192, 2), transform(bytes(bm+at), 480, 4)
        fixed = b'FHT1\x02'+struct.pack('<H', len(header(3)))+header(3)+bytes(256)+table*2
        prefix = struct.pack('<HHHBI', 3, len(vb), len(mb), 32, writer.bits)+vb+mb
        return fixed+prefix+writer.finish(), len(fixed), len(fixed)+len(prefix)

    def test_inline_padding_and_invalid_metadata(self):
        data, start, values = self.mixed()
        decoded, rows = decode(data)
        states = np.frombuffer(decoded, dtype=np.uint8).reshape(3, 3840)
        actual = run_z80(data, states)
        self.assertEqual([r['bits'] for r in actual], [r['bits'] for r in rows])
        for index, mask in ((values, 1), (start+6, 128), (len(data)-1, 1)):
            bad = bytearray(data); bad[index] ^= mask
            with self.assertRaises(ValueError):
                decode(bytes(bad))
        # Invalid literal mask and vector are rejected before CPU execution.
        r = Reader(data); read_header(r)
        n, flags, bits, v, bm, at, encoded = read_group(r, 3)
        for bad_v, bad_bm in ((bytes([83])+v[1:], bm), (v, bm[:2]+b'\x80'+bm[3:])):
            vb = transform(bad_v, 192, 2); mb = transform(bad_bm+at, 480, 4)
            bad = data[:start]+struct.pack('<HHHBI', n, len(vb), len(mb), flags, bits)+vb+mb+encoded
            with self.assertRaises(ValueError):
                decode(bad)

    def test_irq_after_every_instruction_with_mixed_literals(self):
        data, _, _ = self.mixed()
        causal_tests.CausalTileTests.exercise_irq(self, True, hybrid_data=data)


if __name__ == '__main__':
    unittest.main()
