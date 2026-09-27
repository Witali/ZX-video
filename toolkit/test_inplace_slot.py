"""Exercise sector boundaries, overlap, paging and real AY IRQ preservation."""
import struct
import unittest

import ay_interrupt
import bank_local_zx0 as machine
import playback_schedule
import pipelined_frame_z80 as video
from benchmark_compact_screen import STACK, STOP
from benchmark_context_huffman import word
from benchmark_inplace_slot import Harness
from build_zxv_trd import MiniAssembler
from test_fap3_disk import install
from zx0_speed import Token, encode


def block(n, *, literal=False):
    raw = bytes(i % 251 for i in range(n))
    tokens = [Token(0, n)] if literal or n <= 251 else [Token(0, 251), Token(251, n-251, 251)]
    return encode(raw, tokens), raw


def fixture(blocks, first=53):
    stream = b''.join(struct.pack('<HH', len(raw), len(payload))+payload for payload, raw in blocks)
    return Harness(stream, first, inplace=True)


class InplaceSlotTests(unittest.TestCase):
    def test_header_crossings_first_track_and_full_size_bank_rotation(self):
        candidates = {}
        for n in range(1, 520):
            payload, raw = block(n, literal=True)
            candidates.setdefault((len(payload)+4) % 256, (payload, raw))
        for first in (32, 47, 53, 63):
            for offset in (0, 1, 252, 253, 254, 255):
                with self.subTest(first=first, offset=offset):
                    blocks = [candidates[offset], block(15872), block(11), block(280), block(1)]
                    h = fixture(blocks, first); h.cpu.write8(video.SHADOW, 0x1f)
                    for i, (payload, raw) in enumerate(blocks):
                        h.block(payload, raw, i)
                        self.assertEqual(h.cpu.port_7ffd & 8, 8)
                    self.assertEqual(h.results[1]['input_pointer'] & 255, (offset+4) % 256)
                    self.assertTrue(h.finish()['sectors_exact_once'])

    def test_shared_sector_and_short_read_retry(self):
        blocks = [block(800, literal=True)]+[block(1)]*36
        h = fixture(blocks, 47)
        for i, (payload, raw) in enumerate(blocks): h.block(payload, raw, i, short=i == 0)
        result = h.finish()
        self.assertEqual(sum(n for (pc, _), n in h.histogram.items() if pc == h.d['fast_read_retry']), 1)
        self.assertLess(result['sector_reads'], len(blocks))
        self.assertGreater(sum(r['sectors'] == 0 for r in h.results), 20)

    def test_invalid_sizes_fail_before_decoding(self):
        for length, size in ((0, 10), (15873, 10), (100, 0), (100, 16384), (100, 16385)):
            with self.subTest(length=length, size=size):
                h = Harness(struct.pack('<HH', length, size)+bytes(size), 32, inplace=True)
                with self.assertRaisesRegex(AssertionError, 'producer failed'):
                    h.block(bytes(size), bytes(length), 0)

    def test_idle_reload_threshold_wrap_and_first_read(self):
        for before, now, cached, expected, ticks in (
                (100, 163, 3, 3, 111), (100, 164, 3, 254, 160),
                (65520, 48, 3, 254, 160), (100, 356, 3, 254, 144),
                (100, 164, 255, 255, 136)):
            with self.subTest(before=before, now=now, cached=cached):
                h = fixture([block(1)])
                word(h.cpu, h.p['last_read_field'], before); word(h.cpu, h.elapsed_fields, now)
                h.cpu.write8(h.d['cached_track'], cached)
                self.assertEqual(h.call(h.p['check_idle']), ticks)
                self.assertEqual(h.cpu.read8(h.d['cached_track']), expected)
                self.assertEqual(word(h.cpu, h.p['last_read_field']), now)

    def test_long_idle_reloads_head_without_rereading_sector(self):
        blocks = [block(1), block(800, literal=True), block(1200, literal=True)]
        h = fixture(blocks)
        h.block(*blocks[0], 0)
        seeks = len(h.cpu.seek_calls)
        word(h.cpu, h.elapsed_fields, 100)
        h.block(*blocks[1], 1)
        self.assertEqual(len(h.cpu.seek_calls)-seeks, 2)
        self.assertEqual(h.cpu.seek_calls[-1][0], 0x3e44)
        h.block(*blocks[2], 2)
        self.assertTrue(h.finish()['sectors_exact_once'])

    def test_real_ay_irq_after_each_producer_and_decoder_instruction(self):
        blocks = [block(1100, literal=True), block(15872), block(700)]
        h = fixture(blocks); c = h.cpu
        a = MiniAssembler(0x9400)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True, memory_clock=True, audio_irq=True)
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0); a.label('fatal'); a.emit(0x76)
        install(c, 0x9400, a.resolve())
        c.pc, c.sp = a.labels['setup_clock'], STACK; c.push(STOP)
        while c.pc != STOP: c.step()
        c.write8(a.labels['audio_enabled'], 1)
        names = ('a', 'b', 'c', 'd', 'e', 'h', 'l', 'ix', 'iy', 'z', 'carry',
                 'alt_a', 'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l',
                 'alt_z', 'alt_carry', 'port_7ffd', 'sp')
        calls = 0
        def irq(cpu):
            nonlocal calls
            if not cpu.iff1: return 0
            decoding = cpu.decoding; cpu.decoding = False
            word(cpu, a.labels['audio_remaining'], 65535)
            index = cpu.read8(a.labels['audio_read_index'])
            slot = ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
            cpu.write8(slot, 1); cpu.write8(slot+1, 8); cpu.write8(slot+2, calls & 15)
            cpu.write8(a.labels['audio_write_index'], (index+1) & 31)
            before = {n:getattr(cpu, n) for n in names}; started, pc = cpu.tstates, cpu.pc
            cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != pc:
                self.assertNotEqual(cpu.pc, a.labels['fatal'])
                cpu.step()
            self.assertEqual(before, {n:getattr(cpu, n) for n in names})
            self.assertEqual(cpu.ay[8], calls & 15)
            calls += 1
            word(cpu, h.elapsed_fields, calls & 65535)
            cpu.decoding = decoding
            self.assertEqual(word(cpu, a.labels['elapsed_fields']), calls & 65535)
            self.assertEqual(word(cpu, a.labels['audio_underruns']), 0)
            return cpu.tstates-started
        for i, (payload, raw) in enumerate(blocks): h.block(payload, raw, i, interrupt=irq)
        h.finish(); self.assertGreater(calls, 5000)


if __name__ == '__main__': unittest.main()
