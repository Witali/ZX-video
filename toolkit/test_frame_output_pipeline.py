import unittest

import numpy as np

import ay_interrupt
import playback_schedule
import test_fast_fragments
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler
from cell_output_stream import pack
from frame_output_pipeline import Harness, frames, serialized_masks, INPUT, INPUT_END, STACK, STOP
from probe_cell_output_masks import masks
from probe_fast_fragments import encode
from probe_fragment_channels import split
from probe_motion_residual_order import field_order
from test_causal_tiles import predict
from test_hybrid_tiles import header


def fixture(count=5, *, constant_attribute_borders=False):
    states, vectors, residual, selected = test_fast_fragments.FastFragmentTests().fixture(count)
    states[:, :256] = 0; states[:, 2816:3072] = 0
    states[:, 3072:] &= 127
    if constant_attribute_borders:
        states[:,3072:3168] = 1; states[:,3744:3840] = 1
    order = field_order(8).reshape(192, 20)[:, :16]
    previous = bytes(3840)
    for index, state in enumerate(states):
        # Exercise temporal motion, intra prediction and all literal modes in
        # the same frame, including edges and pages crossed by coded input.
        vectors[index, 2::3] = (np.arange(64)*17+index*29) % 82
        predicted = bytearray(predict(previous, vectors[index]))
        for tile, mode in enumerate(vectors[index]):
            if 82 <= mode <= 84:
                for address in order[tile]:
                    y, x = divmod(int(address), 32)
                    source = (address-32 if y else None) if mode == 82 else (
                        (address-1 if x else None) if mode == 83 else (address-64 if y >= 2 else None))
                    predicted[address] = int(state[source]) if source is not None else 0
        residual[index] = state ^ np.frombuffer(predicted, dtype=np.uint8)
        previous = state.tobytes()
    data, detail = encode(header(count), states, vectors, residual, bytes(256),
                         [bytes([8]*256)]*2, selected, group_frames=1)
    separated, _ = split(data, states, vectors, residual)
    flags, _, _ = masks(states)
    return states, pack(separated, flags.tobytes()), detail


class FrameOutputPipelineTests(unittest.TestCase):
    def test_cold_start_and_sequential_frames_share_memory(self):
        states, stream, detail = fixture()
        tables, mapping, packets = frames(stream)
        h = Harness(tables, mapping)
        self.assertEqual(h.init_result['total_tstates'], 397967)
        self.assertEqual(set(detail['fast_kinds']), {85, 86, 87, 88})
        for index, ((group, mask), state) in enumerate(zip(packets, states)):
            row = h.run(group, mask, state.tobytes(), index)
            self.assertEqual(row['stages']['handoff'], 337)
            self.assertGreater(row['coded_bytes'], 256)
            self.assertLessEqual(row['coded_bytes'], INPUT_END-INPUT)
        # Corrupting the next frame map must be caught by actual native RAM.
        with self.assertRaisesRegex(AssertionError, 'screen bytes differ'):
            h = Harness(tables, mapping)
            h.run(packets[0][0], bytes(80), states[0].tobytes(), 0)

    def test_irq_preserves_both_decoders_and_screen_publication(self):
        self.exercise_irq()

    def test_irq_preserves_absolute_attribute_copy(self):
        self.exercise_irq(raw=True)

    def test_irq_preserves_fast_native_dispatch_and_raw_attributes(self):
        self.exercise_irq(raw=True, fast=True)

    def exercise_irq(self, raw=False, fast=False, selective=False, noops=False, empty_noops=False, constant=False,encoded=False):
        states, stream, _ = fixture(2,constant_attribute_borders=constant)
        if raw:
            from raw_attribute_stream import pack
            stream, _ = pack(stream, states, [True, False])
        tables, mapping, packets = frames(stream)
        h = Harness(tables, mapping, raw_attributes=raw, decode_metadata=raw, fast_mask_dispatch=fast,
                    selective_cache=selective,skip_noop_runs=noops,constant_attribute_borders=constant,
                    encoded_noop_runs=encoded)
        coded_masks = serialized_masks(stream) if raw else [None]*len(packets)
        if empty_noops:
            states = np.zeros((2,3840),dtype=np.uint8)
            packets = [((1,0,0,bytes(192),bytes(384),bytes(96),b'',b''),bytes(80))]*2
            coded_masks = [bytes(8)]*2
        a = MiniAssembler(0x9400)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True, memory_clock=True, audio_irq=True)
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76)
        self.assertLess(a.pc, 0x9800)
        cpu = h.cpu; cpu.guarding = False
        for index, value in enumerate(a.resolve()):
            cpu.write8(0x9400+index, value)
        cpu.pc, cpu.sp = a.labels['setup_clock'], STACK
        cpu.push(STOP)
        while cpu.pc != STOP:
            cpu.step()
        cpu.write8(a.labels['audio_enabled'], 1)
        names = ('a', 'b', 'c', 'd', 'e', 'h', 'l', 'ix', 'z', 'carry', 'alt_a',
                 'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l', 'alt_z', 'alt_carry', 'port_7ffd', 'sp')
        calls = 0

        def interrupt(cpu):
            nonlocal calls
            if noops or encoded:
                in_scanner = noops and 0x7a00 <= cpu.pc < h.recon['noop_scanner_end']
                in_encoded = encoded and h.recon['encoded_zero_run'] <= cpu.pc < h.recon['encoded_run_end']
                if not (in_scanner or in_encoded): return 0
            if constant and not h.draw['attributes'] <= cpu.pc < h.draw['attribute_end']:
                return 0
            cpu.guarding = False
            word(cpu, a.labels['audio_remaining'], 65535)
            index = cpu.read8(a.labels['audio_read_index'])
            slot = ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
            cpu.write8(slot, 1); cpu.write8(slot+1, 8); cpu.write8(slot+2, calls & 15)
            cpu.write8(a.labels['audio_write_index'], (index+1) & 31)
            before = {name: getattr(cpu, name) for name in names}
            start, pc = cpu.tstates, cpu.pc
            cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != pc:
                self.assertNotEqual(cpu.pc, a.labels['fatal']); cpu.step()
            self.assertEqual(before, {name: getattr(cpu, name) for name in names})
            self.assertEqual(cpu.ay[8], calls & 15)
            self.assertEqual(cpu.tstates-start, 583)
            calls += 1
            self.assertEqual(word(cpu, a.labels['elapsed_fields']), calls & 65535)
            self.assertEqual(word(cpu, a.labels['audio_underruns']), 0)
            cpu.guarding = True
            return cpu.tstates-start

        for index, ((group, mask), state) in enumerate(zip(packets, states)):
            coverage = None
            if selective:
                from probe_sparse_motion_cache import coverage as source_coverage
                needed = source_coverage(group[3], 32).reshape(24, 4).any(axis=1)
                coverage = np.packbits(needed).tobytes()
            h.run(group, mask, state.tobytes(), index, interrupt, encoded_metadata=coded_masks[index], cache_map=coverage)
        self.assertGreater(calls, 0 if noops or constant or encoded else 20000)
        return calls


if __name__ == '__main__':
    unittest.main()
