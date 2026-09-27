"""All half-row group patterns, exact copy timings and packet-map roundtrips."""
import unittest
import numpy as np

from benchmark_cache_columns import Harness as OldHarness
from benchmark_compact_screen import STACK, STOP
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler
import ay_interrupt
import playback_schedule
import causal_tile_z80 as machine
import half_row_cache as half


class Harness(OldHarness):
    def __init__(self):
        super().__init__(32, True)
        regions, labels, rows = half.build(self.labels, cache_page=0x74)
        regions.append((self.labels['cache_copy'], b'\xc3'+half.SELECTOR.to_bytes(2, 'little')))
        rows.append(dict(address=self.labels['cache_copy'], instruction='JP half selector', tstates=10))
        for at, code in regions:
            for i, value in enumerate(code): self.cpu.write8(at+i, value)
        self.instructions.update({r['address']: r for r in rows})

    def run(self, pairs, source, interrupt=None):
        pairs = np.asarray(pairs, dtype=np.uint8).reshape(24, 2)
        c = self.cpu; c.guarding = False
        for at, blob in ((machine.FRAME, source), (machine.CACHE, b'\xa5'*1024),
                         (machine.CACHE_MAP, np.packbits(pairs).tobytes())):
            for i, value in enumerate(blob): c.write8(at+i, value)
        word(c, self.labels['cache_mask_source'], machine.CACHE_MAP)
        c.write8(self.labels['cache_mask_shift'], 128)
        c.set_hl(machine.FRAME); c.set_de(machine.CACHE+1)
        expected = bytearray(b'\xa5'*1024); first = total = 0
        for rows in [12]+[8]*10+[4]:
            c.guarding = False; c.b, c.c = rows, 0x35
            c.pc, c.sp = self.labels['cache_copy'], STACK; c.push(STOP); c.guarding = True
            while c.pc != STOP:
                pc, before = c.pc, c.tstates; c.step(); ticks = c.tstates-before
                listed = self.instructions[pc]['tstates']
                if ticks not in (listed if isinstance(listed, list) else [listed]):
                    raise AssertionError(('instruction cost', pc, ticks, listed))
                total += ticks
                if interrupt: interrupt(c)
            for group in range(first, first+rows//4):
                for side in range(2):
                    if pairs[group, side]:
                        for row in range(group*4, group*4+4):
                            dst = (row%16)*64+1+16*side; src = row*32+16*side
                            expected[dst:dst+16] = source[src:src+16]
            first += rows//4
            if (c.hl() != machine.FRAME+first*128 or c.de() != machine.CACHE+(first%4)*256+1
                    or c.bc() != 0x35 or c.sp != STACK
                    or bytes(c.read8(machine.CACHE+i) for i in range(1024)) != expected):
                raise AssertionError('copied/untouched cache or register mismatch')
        if (word(c, self.labels['cache_mask_source']) != machine.CACHE_MAP+6
                or c.read8(self.labels['cache_mask_shift']) != 128 or total != half.copy_tstates(pairs)):
            raise AssertionError(('map cursor or timing formula', total, half.copy_tstates(pairs)))
        return total


class HalfRowCacheTests(unittest.TestCase):
    def test_all_group_positions_and_patterns(self):
        h = Harness(); source = bytes((i*71+29)&255 for i in range(3072))
        for value in (0, 1): h.run(np.full((24, 2), value), source)
        for group in range(24):
            for pattern in (1, 2, 3):
                pairs = np.zeros((24, 2), dtype=np.uint8)
                pairs[group] = [pattern>>1, pattern&1]
                h.run(pairs, source)

    def test_packet_roundtrip_and_bounds(self):
        body = bytes(288)
        self.assertEqual(half.narrow(half.widen(body)), body)
        self.assertEqual(len(half.widen(body)), 291)
        with self.assertRaises(ValueError): half.widen(bytes(287))
        with self.assertRaises(ValueError): half.widen(bytes(5)+b'\xff'*3+bytes(280))

    def test_real_ay_irq_after_each_copy_instruction(self):
        h = Harness(); c = h.cpu; c.guarding = False
        a = MiniAssembler(0x9400); ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True, memory_clock=True, audio_irq=True)
        ay_interrupt.emit_variables(a); a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76)
        self.assertLess(a.pc, 0x9800)
        for i, value in enumerate(a.resolve()): c.write8(0x9400+i, value)
        c.pc, c.sp = a.labels['setup_clock'], STACK; c.push(STOP)
        while c.pc != STOP: c.step()
        c.write8(a.labels['audio_enabled'], 1)
        names = ('a', 'b', 'c', 'd', 'e', 'h', 'l', 'ix', 'z', 'carry',
                 'alt_a', 'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l',
                 'alt_z', 'alt_carry', 'port_7ffd', 'sp')
        calls = 0
        def interrupt(cpu):
            nonlocal calls
            cpu.guarding = False; word(cpu, a.labels['audio_remaining'], 65535)
            index = cpu.read8(a.labels['audio_read_index']); slot = 0xa000+index*32
            cpu.write8(slot, 1); cpu.write8(slot+1, 8); cpu.write8(slot+2, calls&15)
            cpu.write8(a.labels['audio_write_index'], (index+1)&31)
            before = {n: getattr(cpu, n) for n in names}; pc, start = cpu.pc, cpu.tstates
            cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != pc:
                self.assertNotEqual(cpu.pc, a.labels['fatal']); cpu.step()
            self.assertEqual(before, {n: getattr(cpu, n) for n in names})
            self.assertEqual(cpu.ay[8], calls&15); self.assertEqual(cpu.tstates-start, 583)
            calls += 1; cpu.guarding = True
        pairs = np.array([[0, 0], [0, 1], [1, 0], [1, 1]]*6, dtype=np.uint8)
        h.run(pairs, bytes((i*71+29)&255 for i in range(3072)), interrupt)
        self.assertGreater(calls, 1000)
        self.assertEqual(word(c, a.labels['audio_underruns']), 0)


if __name__ == '__main__': unittest.main()
