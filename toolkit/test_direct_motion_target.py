"""Paired motion paths, complete frames, placement and real AY interrupts."""
from collections import Counter
import unittest
from unittest.mock import patch

from benchmark_context_huffman import word
from frame_output_pipeline import Harness, frames, OFFSETS
from causal_tile_z80 import VECTOR_PHASE
import cached_huffman_lookahead as lookahead
import direct_motion_target as direct
import test_frame_output_pipeline as pipeline


def harness(tables=None, mapping=None, **options):
    h = Harness(tables or [bytes([8]*256)]*2, mapping or bytes(256),
                carry_huffman=True, register_fragments=True,
                cached_huffman_byte=True, **options)
    lookahead.install_frame(h)
    return h


class DirectMotionTests(unittest.TestCase):
    def test_all_vectors_positions_wraps_registers_and_exact_cycles(self):
        old, new = harness(), harness()
        report = direct.install_stage(new)
        self.assertEqual(report['code_growth_bytes'], 3)
        self.assertLessEqual(new.recon['end'], new.recon['lookahead_refresh'])
        for h in (old, new):
            h.cpu.guarding = False
            for i in range(1024): h.cpu.write8(0x7400+i, (i*37+i//7)&255)
        seen = Counter()
        names = ('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_z','alt_carry',
                 'alt_b','alt_c','alt_d','alt_e','alt_h','alt_l','port_7ffd','sp')
        for vector in range(len(OFFSETS)+1):
            for stripe in (0, 1, 10, 11):
                for column in (0, 1, 14, 15):
                    results = []
                    for h in (old, new):
                        c = h.cpu
                        c.guarding = False
                        c.banks[5][0x2400:0x3000] = b'\xa5'*3072
                        for i, name in enumerate(names):
                            if name not in ('port_7ffd','sp'): setattr(c, name, (i*13+17)&255)
                        c.z, c.carry, c.alt_z, c.alt_carry = True, False, False, True
                        c.a = vector
                        word(c, h.recon['target'], 0x6400+256*stripe+2*column)
                        c.write8(h.recon['stripe_y'], stripe*8)
                        result = h.execute(h.recon['motion'])
                        results.append((bytes(c.banks[5][0x2400:0x3000]),
                                        {n:getattr(c, n) for n in names}, result['total_tstates']))
                    phase = 'clear' if vector == len(OFFSETS) else old.cpu.read8(VECTOR_PHASE+vector)
                    # HL is dead after phases 2/6: the following patch entry
                    # reloads it. All other registers/flags must agree.
                    if phase in (2,6):
                        for item in results:
                            del item[1]['h'], item[1]['l']
                    self.assertEqual(results[0][:2], results[1][:2], (vector, stripe, column))
                    self.assertEqual(results[1][2]-results[0][2], -21 if phase in (2,4,6) else 0)
                    seen[phase] += 1
        self.assertEqual(set(seen), {0,2,4,6,'clear'})
        self.assertEqual(sum(seen.values()), 1312)

    def test_mixed_complete_frames(self):
        states, stream, _ = pipeline.fixture(4)
        tables, mapping, packets = frames(stream)
        old, new = harness(tables, mapping), harness(tables, mapping)
        direct.install_stage(new)
        previous = 0
        entries = {new.recon[f'predict_{phase}'] for phase in (2,4,6)}
        for index, ((group, mask), state) in enumerate(zip(packets, states)):
            before = old.run(group, mask, state.tobytes(), index)
            after = new.run(group, mask, state.tobytes(), index)
            count = sum(n for (pc, _), n in new.histogram.items() if pc in entries)
            self.assertEqual(after['total_tstates']-before['total_tstates'], -21*(count-previous))
            previous = count
        self.assertGreater(previous, 0)

    def test_real_ay_irq_after_every_instruction(self):
        def factory(tables, mapping, **options):
            h = harness(tables, mapping, **options)
            direct.install_stage(h)
            return h
        with patch.object(pipeline, 'Harness', factory):
            self.assertGreater(pipeline.FrameOutputPipelineTests().exercise_irq(), 20000)

    def test_reject_wrong_register_setup_or_no_room(self):
        for bad_setup in (False, True):
            h = harness()
            h.cpu.guarding = False
            h.cpu.write8(h.recon['predict_2'] if bad_setup else h.recon['end'], 0x76)
            with self.assertRaises(ValueError): direct.install_stage(h)

    def test_both_publication_irq_handlers_at_new_setup_boundaries(self):
        import ay_interrupt
        import pipelined_frame_z80 as video
        from pipelined_frame_harness import Clock
        from test_pipelined_frame import fixture
        source = harness()
        change = direct.install_stage(source)
        # Execute the generated setup bytes at their actual new addresses.
        for slow in (False, True):
            h, _, _ = fixture(1, irq_safe_paging=True)
            ticks = []
            clock = Clock(h, ticks)
            c = h.cpu
            c.guarding = False
            word(c, 0xbdbe, 0xbd00 if slow else 0xbd80)
            c.write8(video.ENABLED, 1)
            c.write8(h.audio['audio_enabled'], 1)
            calls = 0
            for phase in (0,2,4,6):
                at = change['labels'][f'predict_{phase}']
                size = 3 if phase == 0 else 5
                for i in range(size): c.write8(at+i, source.cpu.read8(at+i))
                word(c, change['target'], 0x661e)
                c.set_hl(0x1234)
                c.alt_h, c.alt_l = 0x56, 0x78
                c.pc = at
                while c.pc < at+size:
                    c.step()
                    # Publish once after every instruction boundary too.
                    c.write8(video.READY, 1)
                    word(c, video.DEADLINE, 0)
                    tick = bytes([1,8,calls&15])
                    ticks.append(tick)
                    slot = c.read8(h.audio['audio_read_index'])
                    for i, b in enumerate(tick): c.write8(ay_interrupt.QUEUE_BASE+slot*32+i,b)
                    c.write8(h.audio['audio_write_index'], (slot+1)&31)
                    word(c, h.audio['audio_remaining'], 65535)
                    clock.run_irq()
                    calls += 1
                self.assertEqual(c.hl(), 0x661e if phase == 0 else 0x1234)
                self.assertEqual((c.alt_h<<8)|c.alt_l, 0x5678 if phase == 0 else 0x661e)
            self.assertEqual(calls, 10)
            self.assertEqual(clock.ticks, 10)
            self.assertEqual(len(clock.publications), 10)


if __name__ == '__main__':
    unittest.main()
