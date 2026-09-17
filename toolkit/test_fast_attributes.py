"""Check exact attribute addresses, pointers, IRQ safety and timing tables."""
import random
import unittest

import build_fast_sparse_trd as codec
from test_packet_lookahead import word
from validate_fast_sparse import CPU


def payload(indices):
    result = bytearray([len(indices)]); previous = -1; wide = carries = 0
    for index in indices:
        gap = index - previous - 1
        carries += ((previous & 255) + (gap & 255)) > 255
        wide += gap >= 255
        result.extend(bytes([255, gap & 255, gap >> 8]) if gap >= 255 else bytes([gap]))
        result.append((index * 37 + 19) & 127)
        previous = index
    return bytes(result), wide, carries


def execute(player, labels, data, base, irq=False):
    cpu = CPU(player, b'')
    if 'bootstrap' in labels:
        while cpu.pc != labels['start']:
            cpu.step()
    cpu.port_7ffd = 0x17; cpu.sp = 0xBFF0
    if irq:
        from test_packet_lookahead import run
        run(cpu, labels, 'setup_clock')
        cpu.write8(labels['audio_enabled'], 1)
    for bank in (5, 7): cpu.banks[bank][:6912] = bytes([0xA5]) * 6912
    word(cpu, labels, 'attr_base', base)
    start = 0x60FD if 'bootstrap' in labels else 0xA0FD
    for index, value in enumerate(data): cpu.write8(start + index, value)
    cpu.pc = labels['command_attrs_delta']; cpu.ix = start
    cpu.alt_h = 0x12; cpu.alt_l = 0x34
    before = cpu.tstates; interrupts = 0; next_irq = before + 233
    while cpu.pc != labels['command_loop']:
        if irq and cpu.tstates >= next_irq:
            # An empty audio queue is a legal IRQ test path: the ISR still
            # saves/restores all foreground registers. Playback tests verify
            # nonempty queues and every actual 50 Hz AY state separately.
            return_pc = cpu.pc; t = cpu.tstates
            cpu.push(return_pc); cpu.pc = 0xBDBD
            while cpu.pc != return_pc: cpu.step()
            cpu.tstates = t; interrupts += 1; next_irq = t + 233
        cpu.step()
    assert cpu.ix == start + len(data)
    assert cpu.sp == 0xBFF0
    assert (cpu.alt_h, cpu.alt_l) == (0x12, 0x34)
    return cpu, cpu.tstates - before, interrupts


class FastAttributesTests(unittest.TestCase):
    def test_gaps_counts_and_screen_banks(self):
        old = codec.build_player(0, 0, blocked=True, clocked=True)
        new = codec.build_player(0, 0, blocked=True, clocked=True, fast_draw=True)
        cases = [[], list(range(80)), list(range(688, 768)), [0, 256, 767]]
        cases += [[index] for index in range(768)]
        rng = random.Random(3375)
        cases += [sorted(rng.sample(range(768), rng.randrange(1, 81))) for _ in range(100)]
        for indices in cases:
            data, wide, carries = payload(indices)
            for base in (0x5800, 0xD800):
                with self.subTest(indices=indices, base=base):
                    a, at, _ = execute(*old, data, base)
                    b, bt, _ = execute(*new, data, base)
                    for bank in (5, 7):
                        self.assertEqual(a.banks[bank][:6912], b.banks[bank][:6912])
                    self.assertEqual(at, 95 + 251 * len(indices) + 40 * wide)
                    self.assertEqual(bt, 112 + 86 * len(indices) + 55 * wide - carries if indices else 91)
                    self.assertLess(bt, at)

    def test_irq_between_attribute_instructions(self):
        from test_memory_clock import OPTIONS
        player, labels = codec.build_player(3, 2, **(OPTIONS | dict(
            direct_input=True, wrapped_input=True, interleaved=True, ay_noise=True, audio_irq=True)))
        for indices in (list(range(688, 768)), [0, 256, 767]):
            data, _, _ = payload(indices)
            for base in (0x5800, 0xD800):
                before, bt, _ = execute(player, labels, data, base)
                after, at, interrupts = execute(player, labels, data, base, irq=True)
                self.assertGreater(interrupts, 0)
                self.assertEqual(bt, at)
                for bank in (5, 7):
                    self.assertEqual(before.banks[bank][:6912], after.banks[bank][:6912])


if __name__ == '__main__':
    unittest.main()
