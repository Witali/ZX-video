"""Exercise stale cache rows, both edge escapes and exact instruction costs."""
import unittest
from hashlib import sha256

from benchmark_context_huffman import word
from frame_output_pipeline import Harness
from probe_motion_residual_order import field_order
from test_causal_tiles import predict


def delta(vectors, enabled):
    return ((37 if vectors[0] else -1607) +
            (45 if vectors[176] else -1585)) if enabled else 0


class StaticCacheBordersTests(unittest.TestCase):
    def test_sequential_frames_and_all_edge_combinations(self):
        options = dict(raw_attributes=True, fast_mask_dispatch=True, selective_cache=True,
            skip_noop_runs=True, skip_static_stripes=True, unrolled_cache=True,
            sparse_patches=True, fast_noop_scan=True, constant_attribute_borders=True,
            skip_black_borders=True)
        hs = [Harness([bytes([8]*256)]*2, bytes(256), static_cache_borders=v, **options)
              for v in (False, True)]
        order = field_order(8).reshape(192, 20)[:, :16].reshape(-1)
        previous = bytes((i*73+i//32*11) & 255 for i in range(3072))+b'\1'*768
        literals = bytes(previous[int(i)] for i in order)+previous[3072:]
        seed = (1, 64, 0, bytes([85]*192), bytes(384), bytes(96), b'', literals)
        for h in hs: h.run(seed, b'\xff'*80, previous, 0, cache_map=bytes(3))
        # A zero marker must cover a whole unchanged stripe. Active edges use
        # real +/-4 vertical motion, so stale virtual rows would corrupt them.
        from probe_spatial_contexts import OFFSETS
        up, down = OFFSETS.index((0, 4)), OFFSETS.index((0, -4))
        for index in range(1, 13):
            top, bottom = bool(index & 1), bool(index & 2)
            enabled = index <= 8
            vectors = bytearray(192)
            if enabled:
                vectors[16:176] = bytes([up if index & 4 else down])*160
                if top: vectors[:16] = bytes([up])*16
                if bottom: vectors[176:] = bytes([down])*16
            expected = bytes(predict(previous, vectors))
            packet = (1, 128 if enabled else 0, 0, bytes(vectors), bytes(384), bytes(96), b'', b'')
            totals = []
            cursors = []
            for h in hs:
                h.cpu.guarding = False
                # Poison all data slots on every frame; selected rows must
                # be refreshed, while unused virtual rows may remain stale.
                for y in range(16):
                    for x in range(1, 33): h.cpu.write8(0x7400+y*64+x, 0xa5)
                totals.append(h.run(packet, b'\xff'*80, expected, index,
                    cache_map=b'\xff'*3)['total_tstates'])
                cursors.append(tuple(word(h.cpu, h.recon[k]) for k in ('cache_read','cache_write','source')))
            self.assertEqual(totals[1]-totals[0], delta(vectors, enabled))
            self.assertEqual(*cursors)
            previous = expected

    def test_requires_validated_static_stripes(self):
        with self.assertRaisesRegex(ValueError, 'validated static stripes'):
            Harness([bytes([8]*256)]*2, bytes(256), static_cache_borders=True)

    def test_default_reconstruction_binary_unchanged(self):
        # Captured by executing the same configuration on main at 6e724f4.
        h = Harness([bytes([8]*256)]*2,bytes(256),raw_attributes=True,
            fast_mask_dispatch=True,selective_cache=True,skip_noop_runs=True,
            skip_static_stripes=True,unrolled_cache=True,sparse_patches=True,fast_noop_scan=True)
        data = bytes(h.cpu.read8(a) for a in range(0x8000,h.recon['end']))
        self.assertEqual(sha256(data).hexdigest(),
            '11664fb53ef1994df8fcb026125af22fbaad95d52809459b501a1fb6bd4eb78d')

    def test_irq_during_new_branches(self):
        from test_frame_output_pipeline import FrameOutputPipelineTests
        for empty in (False,True):
            self.assertGreater(FrameOutputPipelineTests().exercise_irq(raw=True,fast=True,
                selective=True,noops=True,static=True,static_cache_borders=True,empty_noops=empty), 0)


if __name__ == '__main__': unittest.main()
