import json
from pathlib import Path
import struct
import unittest

import numpy as np

import probe_raw_patches as codec
from probe_motion_entropy import Reader
from probe_motion_metadata import transform
from test_causal_tiles import predict
from test_hybrid_tiles import header
import test_causal_tiles as causal_tests
from benchmark_causal_tiles import Harness
import causal_tile_z80 as machine


def run_z80(data, states):
    r = Reader(data)
    kind, _, remaining, mapping, tables, _ = codec.read_header(r)
    h = Harness(tables, mapping, codec.OFFSETS, skip_empty=True, hybrid=True, raw_kind=kind)
    start, rows = 0, []
    while remaining:
        n, _, bits, vectors, bm, at, encoded = codec.read_group(r, remaining)
        h.begin(encoded, vectors, bm, at)
        for i in range(n):
            got = h.run(i, states[start+i].tobytes())
            raw_base = 0
            for tile, v in enumerate(vectors[i*192:(i+1)*192]):
                if v & 128:
                    a, b = bm[i*384+tile*2:i*384+tile*2+2]
                    raw_base += 649 if a and b else 444 if a else 434
            assert got['stages'].get('raw_patch', 0) == raw_base+(20 if kind == 0 else 27)*got['raw_values']+10*got['unaligned_raw_tiles']
            rows.append(got)
        assert h.position() == bits
        start += n; remaining -= n
    r.end()
    return rows


class RawPatchTests(unittest.TestCase):
    def test_all_alphabets_motion_and_short_groups(self):
        rng = np.random.default_rng(716)
        states, residual, vectors, previous = [], [], [], bytes(3840)
        for i in range(5):
            v = bytes((tile+i*19) % 82 for tile in range(192))
            predicted = np.frombuffer(predict(previous, v), dtype=np.uint8)
            current = predicted.copy()
            positions = np.arange(i % 3, 3840, 1+i % 3)
            current[positions] ^= rng.integers(1, 256, size=len(positions), dtype=np.uint8)
            states.append(current); residual.append(current ^ predicted); vectors.append(list(v))
            previous = current.tobytes()
        states, residual, vectors = (np.asarray(a, dtype=np.uint8) for a in (states, residual, vectors))
        for kind in range(3):
            for threshold in (None, 64, 32, 0):
                with self.subTest(kind=kind, threshold=threshold):
                    data, detail = codec.encode(header(5), states, vectors, residual, bytes(256), [bytes([8]*256)]*2, kind, threshold, cap=4500)
                    actual, rows = codec.decode(data)
                    self.assertEqual(actual, states.tobytes())
                    self.assertEqual(rows, detail['frames'])
                    self.assertGreater(len(detail['groups']), 1)
                    if kind < 2 and threshold in (64, 0):
                        measured = run_z80(data, states)
                        for expected, actual in zip(rows, measured):
                            self.assertEqual(actual['bits'], expected['bits'])
                            self.assertEqual(actual['values'], expected['coded_values'])
                            self.assertEqual(actual['raw_values'], expected['raw_values'])
                            self.assertEqual(actual['raw_tiles'], expected['raw_tiles'])

    def mixed(self, kind):
        table = bytes([1]+[0]*254+[1])
        states = np.zeros((3, 3840), dtype=np.uint8)
        states[0, [0, 2, 3, 3072]] = 255
        states[1] = states[0]; states[1, [2, 3]] = 0
        vectors = np.zeros((3, 192), dtype=np.uint8); vectors[2, 0] = 80
        states[2] = np.frombuffer(predict(states[1].tobytes(), vectors[2]), dtype=np.uint8)
        states[2, 3073] = 255
        predictions = np.zeros_like(states)
        for i in (1, 2):
            predictions[i] = np.frombuffer(predict(states[i-1].tobytes(), vectors[i]), dtype=np.uint8)
        data, detail = codec.encode(header(3), states, vectors, states ^ predictions,
            bytes(256), [table]*2, kind, 2)
        return data, detail, states

    def test_mixed_alignment_zero_values_and_invalid_streams(self):
        for kind in range(3):
            data, detail, states = self.mixed(kind)
            actual, rows = codec.decode(data)
            self.assertEqual(actual, states.tobytes())
            self.assertEqual(rows, detail['frames'])
            r = Reader(data); codec.read_header(r); start = r.pos
            n, flags, bits, v, bm, at, encoded = codec.read_group(r, 3)
            values = r.pos-len(encoded)
            for bad in (data[:-1], data+b'!', b'bad!'+data[4:]):
                with self.assertRaises(ValueError):
                    codec.decode(bad)
            for pos in (values, start+6, len(data)-1):
                bad = bytearray(data); bad[pos] ^= 1
                with self.assertRaises(ValueError):
                    codec.decode(bytes(bad))
            for index, new_vector in ((0, 82), (3, 128)):
                bad_v = bytearray(v); bad_v[index] = new_vector
                vb, mb = transform(bytes(bad_v), 192, 2), transform(bm+at, 480, 4)
                bad = data[:start]+struct.pack('<HHHBI', n, len(vb), len(mb), flags, bits)+vb+mb+encoded
                with self.assertRaises(ValueError):
                    codec.decode(bad)

    def test_irq_after_every_instruction(self):
        for kind in (0, 1):
            data, _, _ = self.mixed(kind)
            causal_tests.CausalTileTests.exercise_irq(self, True, raw_data=data)

    def test_fht_machine_unchanged(self):
        root = Path(__file__).parent
        report = json.loads((root/'hybrid_tiles_control_cpu.json').read_text(encoding='utf-8'))
        profile = json.loads((root/'direct_values_profile.json').read_text(encoding='utf-8'))
        model = next(r for r in profile['rows'] if r['name'] == 'direct')
        group = next(r for r in model['groups'] if r['bitmap_contexts'] == 16)
        code, labels, listing, _ = machine.build([bytes(t) for t in group['tables']], group['context_map'], codec.OFFSETS, skip_empty=True, hybrid=True)
        self.assertEqual(code.hex(), report['code_hex'])
        self.assertEqual(labels, report['labels'])
        self.assertEqual(listing, report['instruction_listing'])


if __name__ == '__main__':
    unittest.main()
