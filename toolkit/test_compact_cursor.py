"""Cursor boundaries, complete mixed frames and actual instruction-boundary IRQ."""
from collections import Counter
import unittest

import compact_cursor as patch
from benchmark_context_huffman import word
from frame_output_pipeline import Harness, frames
from test_frame_output_pipeline import fixture


def harness():
    return Harness([bytes([8]*256)]*2, bytes(256), raw_attributes=True,
        fast_mask_dispatch=True, selective_cache=True, skip_noop_runs=True, fast_noop_scan=True)


class CompactCursorTests(unittest.TestCase):
    def test_ordinary_tile_at_every_column_and_page(self):
        h = harness()
        report = patch.install_stage(h)
        block = report['patches'][0]
        c = h.cpu
        for high in range(0x64, 0x70):
            for column in range(0, 32, 2):
                for carry in (False, True):
                    word(c, report['target'], 256*high+column)
                    c.carry = carry
                    c.pc = block['start']
                    before = c.tstates
                    while c.pc != block['end']:
                        c.step()
                    self.assertEqual(c.tstates-before, 33)
                    self.assertEqual(word(c, report['target']), 256*high+column+2)

    def test_noop_runs_columns_masks_and_vector_page_boundaries(self):
        old, new = harness(), harness()
        patch.install_stage(new)
        for offset in (0, 1, 127, 240, 254, 255):
            for column in range(16):
                for length in range(1, 17-column):
                    for following in ('end', 'vector', 'patch'):
                        if column+length == 16 and following != 'end':
                            continue
                        totals = []
                        for h in (old, new):
                            c = h.cpu
                            c.guarding = False
                            vector = 0xa700+offset
                            masks = 0xa4fe
                            for i in range(17): c.write8(vector+i, 0)
                            for i in range(34): c.write8(masks+i, 0)
                            if following == 'vector': c.write8(vector+length, 81)
                            if following == 'patch': c.write8(masks+length*2+(offset&1), 128)
                            word(c, h.recon['vectors'], vector)
                            word(c, h.recon['bitmap_masks'], masks)
                            word(c, h.recon['target'], 0x6600+column*2)
                            left = length if following == 'end' else 16-column
                            c.write8(h.recon['tiles_left'], left)
                            c.pc = h.recon['tile']
                            start = c.tstates
                            while True:
                                row = h.instructions[c.pc]
                                before = c.tstates
                                c.step()
                                allowed = row['tstates']
                                self.assertIn(c.tstates-before, allowed if isinstance(allowed,list) else [allowed])
                                if c.pc in (h.recon['tile'], h.recon['stripe_done']): break
                            totals.append(c.tstates-start)
                            self.assertEqual((word(c,h.recon['vectors']), word(c,h.recon['bitmap_masks']),
                                word(c,h.recon['target']), c.read8(h.recon['tiles_left'])),
                                (vector+length, masks+2*length, 0x6600+2*(column+length), left-length))
                        self.assertEqual(totals[1]-totals[0], -20)

    def test_complete_mixed_frames_and_exact_delta(self):
        states, stream, _ = fixture(4)
        tables, mapping, packets = frames(stream)
        old, new = [Harness(tables, mapping, skip_noop_runs=True, fast_noop_scan=True) for _ in range(2)]
        report = patch.install_stage(new)
        starts = {v['start']: v['name'] for v in report['patches']}
        prior = Counter()
        for index, ((group, native), state) in enumerate(zip(packets, states)):
            before = old.run(group, native, state.tobytes(), index)
            after = new.run(group, native, state.tobytes(), index)
            now = Counter()
            for (pc, ticks), n in old.histogram.items():
                if pc in starts: now[starts[pc]] += n
            counts = now-prior
            prior = now
            self.assertEqual(after['total_tstates']-before['total_tstates'], patch.delta(counts))
        self.assertGreater(prior['tile'], 0)

    def test_actual_ay_and_video_irq_at_each_replacement_boundary(self):
        import ay_interrupt
        import pipelined_frame_z80 as video
        from pipelined_frame_harness import Clock
        from test_pipelined_frame import fixture as video_fixture
        for slow in (False, True):
            h, _, _ = video_fixture(1, irq_safe_paging=True)
            ticks = []
            clock = Clock(h, ticks)
            c = h.cpu
            c.guarding = False
            report = patch.build(c.read8, h.instructions.values(), h.frame.recon)
            word(c, 0xbdbe, 0xbd00 if slow else 0xbd80)
            c.write8(video.ENABLED, 1)
            c.write8(video.READY, 1)
            word(c, video.DEADLINE, 0)
            c.write8(h.audio['audio_enabled'], 1)
            calls = 0
            for block in report['patches']:
                for i, b in enumerate(bytes.fromhex(block['code_hex'])): c.write8(block['start']+i,b)
                word(c, report['target'], 0x661e if block['name']=='tile' else 0x660e)
                c.c = 9
                c.pc = block['start']
                while c.pc != block['end']:
                    c.step()
                    tick = bytes([1, 8, calls&15])
                    ticks.append(tick)
                    slot = c.read8(h.audio['audio_read_index'])
                    for i,b in enumerate(tick): c.write8(ay_interrupt.QUEUE_BASE+slot*32+i,b)
                    c.write8(h.audio['audio_write_index'], (slot+1)&31)
                    word(c, h.audio['audio_remaining'], 65535)
                    clock.run_irq()
                    calls += 1
                self.assertEqual(word(c, report['target']), 0x6620)
            self.assertEqual(calls, 9)
            self.assertEqual(clock.ticks, calls)
            self.assertEqual(len(clock.publications), 1)


if __name__ == '__main__':
    unittest.main()
