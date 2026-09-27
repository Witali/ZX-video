"""Two-byte cache boundaries, mixed callers, motion registers and actual IRQ."""
import unittest
from unittest.mock import patch

from benchmark_prefix_huffman import Harness as Prefix, INPUT, STOP, STACK
from probe_motion_entropy import codes_for
from test_prefix_huffman_z80 import candidate
from frame_output_pipeline import Harness as Frame, frames
import test_frame_output_pipeline as pipeline
import test_context_huffman_z80 as context_tests
import cached_huffman_lookahead as lookahead


def primitive(tables, mapping, new):
    h = Prefix(tables, mapping, carry_huffman=True, cached_byte=True)
    if new:
        report = lookahead.build(h.cpu.read8, h.listing, h.labels)
        for region in report['regions']:
            for i, value in enumerate(bytes.fromhex(region['code_hex'])):
                h.cpu.write8(region['address']+i, value)
        h.labels = report['labels']
        h.listing = report['listing']
    h.timings = {r['address']: r['tstates'] for r in h.listing}
    return h


def call(h, context, encoded, offset, guards=b'\xa5\x3c'):
    c = h.cpu
    c.guarding = False
    h.begin(encoded)
    for i, value in enumerate(guards): c.write8(INPUT+len(encoded)+i, value)
    c.input_end = INPUT+len(encoded)+len(guards)
    c.ix, c.c = INPUT, 0xf8+offset
    c.b, c.e = c.read8(INPUT), c.read8(INPUT+1)
    c.a = h.mapping.index(context) if context < len(h.tables)-1 else 0
    c.pc = h.labels['bitmap' if context < len(h.tables)-1 else 'attribute']
    c.sp = STACK
    c.push(STOP)
    c.guarding = True
    start = c.tstates
    while c.pc != STOP:
        pc, before = c.pc, c.tstates
        c.step()
        ticks = h.timings[pc]
        if c.tstates-before not in (ticks if isinstance(ticks, list) else [ticks]):
            raise AssertionError(('instruction timing', pc, ticks, c.tstates-before))
    if c.sp != STACK: raise AssertionError('stack not restored')
    return c.a, (c.ix-INPUT)*8+(c.c&7), c.tstates-start


class LookaheadTests(unittest.TestCase):
    def test_all_codes_offsets_and_arbitrary_guards(self):
        tables, mapping = candidate()
        old, new = [primitive(tables, mapping, option) for option in (False, True)]
        seen = set()
        for context, table in enumerate(tables):
            for value, (code, length) in enumerate(codes_for(255, table)):
                if not length: continue
                for offset in range(8):
                    encoded = (code << ((-offset-length)%8)).to_bytes((offset+length+7)//8, 'big')
                    before = call(old, context, encoded, offset)
                    after = call(new, context, encoded, offset)
                    self.assertEqual(before[:2], (value, offset+length))
                    self.assertEqual(after[:2], before[:2])
                    expected = 18 if length > 8 else -7 if offset+length >= 8 else -11
                    self.assertEqual(after[2]-before[2], expected)
                    self.assertEqual((new.cpu.b, new.cpu.e),
                                     (new.cpu.read8(new.cpu.ix), new.cpu.read8(new.cpu.ix+1)))
                    seen.add(expected)
        self.assertEqual(seen, {-11, -7, 18})

    def test_second_guard_is_a_real_contract_requirement(self):
        tables = [bytes([8]*256)]*2
        h = primitive(tables, bytes(256), True)
        with self.assertRaises((AssertionError, RuntimeError)):
            call(h, 0, b'\x37', 0, guards=b'\xa5')
        self.assertEqual(call(h, 0, b'\x37', 0)[:2], (0x37, 8))

    def test_long_codes_with_real_ay_irq_at_every_instruction(self):
        tables, mapping = candidate()

        def factory():
            h = primitive(tables, mapping, True)
            original_begin = h.begin

            def begin(encoded):
                original_begin(encoded)
                h.cpu.write8(INPUT+len(encoded)+1, 0x3c)
                h.cpu.input_end += 1

            def run(pairs, expected, interrupt):
                c = h.cpu
                c.ix, c.c = INPUT, 0xf8
                c.b, c.e = c.read8(INPUT), c.read8(INPUT+1)
                bits = 0
                for (attribute, predicted), value in zip(pairs, expected, strict=True):
                    context = len(tables)-1 if attribute else mapping[predicted]
                    bits += tables[context][value]
                    c.a = predicted
                    c.sp = STACK
                    c.guarding = False
                    c.push(STOP)
                    c.pc = h.labels['attribute' if attribute else 'bitmap']
                    c.guarding = True
                    while c.pc != STOP:
                        pc, before = c.pc, c.tstates
                        c.step()
                        ticks = h.timings[pc]
                        self.assertIn(c.tstates-before, ticks if isinstance(ticks, list) else [ticks])
                        if c.pc != STOP: interrupt(c)
                    self.assertEqual((c.a, c.sp, (c.ix-INPUT)*8+(c.c&7)), (value, STACK, bits))
                    self.assertEqual((c.b, c.e), (c.read8(c.ix), c.read8(c.ix+1)))
            h.begin, h.run = begin, run
            return h

        context_tests.ContextHuffmanZ80Tests().exercise_ay_irq(
            tables, mapping, factory, 'benchmark_prefix_huffman.PAIRS')

    def test_mixed_frames_and_empty_stream(self):
        states, stream, _ = pipeline.fixture(4)
        tables, mapping, packets = frames(stream)
        old, new = [Frame(tables, mapping, carry_huffman=True, register_fragments=True,
                          cached_huffman_byte=True) for _ in range(2)]
        report = lookahead.install_frame(new)
        self.assertEqual(len(report['motion_changes']), 117)
        for index, ((group, mask), state) in enumerate(zip(packets, states)):
            before = old.run(group, mask, state.tobytes(), index)
            after = new.run(group, mask, state.tobytes(), index)
            # The fixture uses eight-bit codes; every symbol crosses a byte.
            self.assertEqual(after['total_tstates']-before['total_tstates'], 46-7*len(group[6]))
        empty = Frame(tables, mapping, carry_huffman=True, cached_huffman_byte=True)
        lookahead.install_frame(empty)
        empty.run((1, 0, 0, bytes(192), bytes(384), bytes(96), b'', b''), bytes(80), bytes(3840), 0)

    def test_actual_frame_irq_after_each_instruction(self):
        def factory(tables, mapping, **options):
            h = Frame(tables, mapping, **options, carry_huffman=True,
                      register_fragments=True, cached_huffman_byte=True)
            lookahead.install_frame(h)
            return h
        with patch.object(pipeline, 'Harness', factory):
            pipeline.FrameOutputPipelineTests().exercise_irq()


if __name__ == '__main__':
    unittest.main()
