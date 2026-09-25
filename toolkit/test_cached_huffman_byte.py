"""Cached input byte: bit boundaries, long returns, callers and IRQ lifetime."""
import unittest
from unittest.mock import patch

from benchmark_prefix_huffman import Harness, INPUT
from probe_motion_entropy import codes_for
from test_prefix_huffman_z80 import candidate
from probe_context_values import pack
import test_context_huffman_z80 as irq
import test_frame_output_pipeline as pipeline
from frame_output_pipeline import Harness as Frame, frames
import causal_tile_z80
from probe_spatial_contexts import OFFSETS


def paired_codes(tables, mapping):
    old = Harness(tables, mapping, carry_huffman=True)
    new = Harness(tables, mapping, carry_huffman=True, cached_byte=True)
    seen, cases = {}, 0
    for context, table in enumerate(tables):
        pair = (1, 0) if context == len(tables)-1 else (0, mapping.index(context))
        for value, (code, length) in enumerate(codes_for(255, table)):
            if not length:
                continue
            for offset in range(8):
                encoded = (code << ((-offset-length) % 8)).to_bytes((offset+length+7)//8, 'big')
                costs = []
                for h in (old, new):
                    h.begin(encoded)
                    h.cpu.write8(INPUT+len(encoded), 0xa5)
                    h.cpu.write8(h.labels['bit_page'], h.bit_base+offset)
                    costs.append(h.run([pair], bytes([value]))['primitive_tstates'])
                    assert h.position() == offset+length
                kind = 'long' if length > 8 else 'cross' if offset+length >= 8 else 'inside'
                delta = costs[1]-costs[0]
                assert delta == (-15 if kind == 'inside' else 4), (context, value, offset, costs)
                seen.setdefault(kind, set()).add(delta)
                cases += 1
    return dict(paired_cases=cases, deltas={k:sorted(v) for k,v in seen.items()},
                old_primitive_bytes=old.labels['primitive_end']-0x8000,
                new_primitive_bytes=new.labels['primitive_end']-0x8000,
                code_hex=new.code.hex(), labels=new.labels, listing=new.listing)


class CachedByteTests(unittest.TestCase):
    def test_every_code_on_each_bit_offset(self):
        report = paired_codes(*candidate())
        self.assertEqual(report['new_primitive_bytes']-report['old_primitive_bytes'], 4)
        self.assertEqual(report['deltas'], dict(inside=[-15], cross=[4], long=[4]))

    def test_cached_lifetime_across_mixed_symbols_chunks_and_final_guard(self):
        tables, mapping = candidate()
        pairs, values, contexts = [], bytearray(), []
        for context, table in enumerate(tables):
            available = sorted((length, value) for value, length in enumerate(table) if length)
            for _, value in (available[0], available[-1], available[1], available[-2])*2:
                pairs.append((1, 0) if context == len(tables)-1 else (0, mapping.index(context)))
                values.append(value); contexts.append(context)
        _, encoded = pack(values, contexts, [codes_for(255, table) for table in tables])
        h = Harness(tables, mapping, carry_huffman=True, cached_byte=True)
        h.begin(encoded)
        for at in range(0, len(values), 13):
            h.run(pairs[at:at+13], values[at:at+13])
        self.assertEqual(h.run([], b'')['total_tstates'], 27)
        self.assertEqual(h.position(), sum(tables[c][v] for c, v in zip(contexts, values)))

    def test_decoder_ay_irq_after_each_instruction(self):
        tables, mapping = candidate()
        irq.ContextHuffmanZ80Tests().exercise_ay_irq(tables, mapping,
            lambda: Harness(tables, mapping, carry_huffman=True, cached_byte=True),
            'benchmark_prefix_huffman.PAIRS')

    def test_mixed_frame_register_lifetime_and_empty_guard(self):
        states, stream, _ = pipeline.fixture(3)
        tables, mapping, packets = frames(stream)
        hs = [Frame(tables, mapping, carry_huffman=True, register_fragments=True,
                    cached_huffman_byte=cached) for cached in (False, True)]
        for i, ((group, native), state) in enumerate(zip(packets, states)):
            rows = [h.run(group, native, state.tobytes(), i) for h in hs]
            self.assertEqual(rows[1]['total_tstates']-rows[0]['total_tstates'], 19+4*len(group[6]))
        h = Frame(tables, mapping, carry_huffman=True, cached_huffman_byte=True)
        group = (1, 0, 0, bytes(192), bytes(384), bytes(96), b'', b'')
        h.run(group, bytes(80), bytes(3840), 0)

    def test_frame_ay_irq_after_each_instruction(self):
        def factory(tables, mapping, **options):
            return Frame(tables, mapping, **options, carry_huffman=True,
                         register_fragments=True, cached_huffman_byte=True)
        with patch.object(pipeline, 'Harness', factory):
            pipeline.FrameOutputPipelineTests().exercise_irq()

    def test_reject_unsupported_register_contract(self):
        tables, mapping = candidate()
        with self.assertRaisesRegex(ValueError, 'requires carry'):
            Harness(tables, mapping, cached_byte=True)
        with self.assertRaisesRegex(ValueError, 'separate literal'):
            causal_tile_z80.build(tables, mapping, OFFSETS, carry_huffman=True, cached_huffman_byte=True)


if __name__ == '__main__':
    unittest.main()
