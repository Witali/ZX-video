import unittest

import numpy as np

import probe_spatial_contexts as spatial
from probe_hybrid_tiles import encode as encode_fht
from test_hybrid_tiles import header
from test_causal_tiles import predict
from probe_spatial_tiles import choose
from probe_spatial_predictors import choose as choose_extended
from optimize_spatial_tiles import choose_coded
from probe_motion_entropy import Reader
from benchmark_causal_tiles import Harness
import causal_tile_z80 as machine
import test_causal_tiles as causal_tests


class SpatialContextTests(unittest.TestCase):
    def test_every_model_uses_reconstructed_neighbours_and_edges(self):
        rng = np.random.default_rng(71623)
        states, residual, vectors, previous = [], [], [], bytes(3840)
        for frame in range(9):
            v = bytes((t+frame*13) % 82 for t in range(192))
            predicted = np.frombuffer(predict(previous, v), dtype=np.uint8)
            target = predicted.copy()
            positions = np.arange(0, 3840, 1+frame % 3)
            target[positions] ^= rng.integers(1, 256, len(positions), dtype=np.uint8)
            states.append(target); residual.append(target ^ predicted); vectors.append(list(v))
            previous = target.tobytes()
        states, residual, vectors = (np.asarray(x, dtype=np.uint8) for x in (states, residual, vectors))
        tables, mapping = [bytes([8]*256)]*2, bytes(256)
        for model in range(len(spatial.MODELS)):
            with self.subTest(model=model):
                data, detail = spatial.encode(header(9), states, vectors, residual, model, mapping, tables, cap=4500)
                decoded, rows = spatial.decode(data)
                self.assertEqual(decoded, states.tobytes())
                self.assertEqual(rows, detail['frames'])
                self.assertGreater(len(detail['groups']), 2)
                self.assertLessEqual(max(g['encoded_bytes'] for g in detail['groups']), 4500)
                for bad in (data[:-1], data+b'!', data[:4]+bytes([255])+data[5:]):
                    with self.assertRaises(ValueError):
                        spatial.decode(bad)
                if model == 0:
                    control, _ = encode_fht(header(9), states, vectors, residual, mapping, tables, None, cap=4500)
                    self.assertEqual(b'FHT1'+data[5:], control)

    def test_arrays_keep_raster_boundaries(self):
        current = np.arange(3072, dtype=np.uint16).astype(np.uint8).reshape(1, 3072)
        states = np.zeros((1, 3840), dtype=np.uint8); states[:, :3072] = current
        residual = states ^ 0x55
        above, values = spatial.model_arrays(states, residual, 1)
        left, _ = spatial.model_arrays(states, residual, 2)
        np.testing.assert_array_equal(values, current)
        np.testing.assert_array_equal(above[:, :32], np.zeros((1, 32), dtype=np.uint8))
        np.testing.assert_array_equal(above[:, 32:], current[:, :-32])
        np.testing.assert_array_equal(left[:, ::32], np.zeros((1, 96), dtype=np.uint8))
        np.testing.assert_array_equal(left.reshape(96, 32)[:, 1:], current.reshape(96, 32)[:, :-1])

    def test_intra_above_applies_corrections_before_the_next_row(self):
        rng = np.random.default_rng(912)
        states = rng.integers(0, 256, (3, 3840), dtype=np.uint8)
        # Vertical areas make intra prediction useful; changed first rows
        # must propagate inside tiles and over stripe boundaries.
        rows = states[:, :3072].reshape(3, 96, 32)
        rows[:, 1:] = rows[:, :1]
        rows[:, 7:18, 0] = 0x33
        rows[:, 23:33, 31] = 0xcc
        residual = states.copy(); residual[1:] ^= states[:-1]
        vectors = np.zeros((3, 192), dtype=np.uint8)
        vectors, residual, intra = choose(states, vectors, residual)
        self.assertTrue(intra.any())
        self.assertTrue(np.any(residual[:, :32]))
        for model in (0, 1):
            data, detail = spatial.encode(header(3), states, vectors, residual, model,
                bytes(256), [bytes([8]*256)]*2)
            actual, decoded = spatial.decode(data)
            self.assertEqual(actual, states.tobytes())
            self.assertEqual(decoded, detail['frames'])
            if model == 0:
                old = self.run_z80(data, states)
                new = self.run_z80(data, states, extended=True)
                for i, (before, after) in enumerate(zip(old, new)):
                    delta = 34*int(np.count_nonzero(vectors[i] == 82))
                    self.assertEqual(after['total_tstates']-before['total_tstates'], delta)
                    self.assertEqual(after['stages'].get('intra', 0)-before['stages'].get('intra', 0), delta)

    def run_z80(self, data, states, *, extended=False):
        r = Reader(data)
        model, _, remaining, mapping, tables = spatial.read_header(r)
        self.assertEqual(model, 0)
        h = Harness(tables, mapping, spatial.OFFSETS, skip_empty=True, hybrid=True, intra_above=True, intra_extended=extended)
        start, results = 0, []
        while remaining:
            n, _, bits, v, bm, at, encoded = spatial.read_group(r, remaining)
            h.begin(encoded, v, bm, at)
            for i in range(n):
                got = h.run(i, states[start+i].tobytes())
                results.append(got)
                expected = 0
                for tile, vector in enumerate(v[i*192:(i+1)*192]):
                    if vector >= 82:
                        count = sum(b.bit_count() for b in bm[i*384+tile*2:i*384+tile*2+2])
                        expected += machine.intra_tstates(vector, tile, count, extended=extended)
                self.assertEqual(got['stages'].get('intra', 0), expected)
            self.assertEqual(h.position(), bits)
            start += n; remaining -= n
        r.end()
        return results

    def test_irq_during_intra_and_motion(self):
        states = np.zeros((3, 3840), dtype=np.uint8)
        states[0, :3072] = 255; states[0, 3072] = 255
        states[1] = states[0]; states[1, 1:3072:32] = 0
        v = np.zeros((3, 192), dtype=np.uint8)
        v[:2] = 82; v[2, 0] = 80
        states[2] = np.frombuffer(predict(states[1].tobytes(), v[2]), dtype=np.uint8)
        residual = states.copy()
        for i in (0, 1):
            residual[i, 32:3072] ^= states[i, :3040]
            if i:
                residual[i, 3072:] ^= states[i-1, 3072:]
        residual[2] = 0
        table = bytes([1]+[0]*254+[1])
        data, _ = spatial.encode(header(3), states, v, residual, 0, bytes(256), [table]*2)
        self.run_z80(data, states)
        causal_tests.CausalTileTests.exercise_irq(self, True, spatial_data=data)

    def test_extended_predictors_and_coded_selection_are_causal(self):
        states = np.zeros((2, 3840), dtype=np.uint8)
        bitmap = states[:, :3072].reshape(2, 96, 32)
        bitmap[:, ::2] = np.arange(32, dtype=np.uint8)*7
        bitmap[:, 1::2] = 255-np.arange(32, dtype=np.uint8)*7
        bitmap[:, :, :16] = np.where(np.arange(96)[None, :, None] % 2, 0x33, 0xcc)
        bitmap[:, 16:48] = bitmap[:, 16:17]
        states[:, 3072:] = 7
        residual = states.copy(); residual[1:] ^= states[:-1]
        vectors = np.zeros((2, 192), dtype=np.uint8)
        v, delta = choose_extended(states, vectors, residual)
        for value in (82, 83, 84):
            self.assertTrue(np.any(v == value), value)
        table, mapping = [bytes([8]*256)]*2, bytes(256)
        for vv, dd in ((v, delta), choose_coded(states, vectors, residual, mapping, table)[:2]):
            data, detail = spatial.encode(header(2), states, vv, dd, 0, mapping, table)
            actual, rows = spatial.decode(data)
            self.assertEqual(actual, states.tobytes()); self.assertEqual(rows, detail['frames'])
            self.run_z80(data, states, extended=True)
        expected_v, expected_d, _ = choose(states, vectors, residual)
        only_above_v, only_above_d = choose_extended(states, vectors, residual, ['above'])
        np.testing.assert_array_equal(only_above_v, expected_v)
        np.testing.assert_array_equal(only_above_d, expected_d)

    def test_extended_z80_edges_corrections_and_irq(self):
        # Three all-intra frames exercise first rows, left edges and stripes.
        # Corrections on both bytes must feed the next causal prediction.
        rng = np.random.default_rng(83084)
        states = rng.choice(np.array([0, 255], dtype=np.uint8), (3, 3840))
        vectors = np.array([np.full(192, v, dtype=np.uint8) for v in (82, 83, 84)])
        residual = states.copy()
        for i, v in enumerate((82, 83, 84)):
            rows = states[i, :3072].reshape(96, 32)
            previous = np.zeros_like(rows)
            if v == 82:
                previous[1:] = rows[:-1]
            elif v == 83:
                previous[:, 1:] = rows[:, :-1]
            else:
                previous[2:] = rows[:-2]
            residual[i, :3072] ^= previous.ravel()
            if i:
                residual[i, 3072:] ^= states[i-1, 3072:]
        table = bytes([1]+[0]*254+[1])
        data, _ = spatial.encode(header(3), states, vectors, residual, 0, bytes(256), [table]*2)
        self.assertEqual(spatial.decode(data)[0], states.tobytes())
        self.run_z80(data, states, extended=True)
        causal_tests.CausalTileTests.exercise_irq(self, True, spatial_data=data, spatial_extended=True)


if __name__ == '__main__':
    unittest.main()
