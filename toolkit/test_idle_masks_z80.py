"""Opcode/timing tests for idle metadata, with poisoned, write-guarded holes."""
import unittest
import random

import idle_masks_z80 as idle
from frame_metadata_z80 import MASKS, FLAGS
from probe_motion_metadata import transform
from test_compiled_masks_z80 import CompiledMaskTests, INPUT
from benchmark_context_huffman import word


class IdleMaskTests(unittest.TestCase):
    install = CompiledMaskTests.install
    read = CompiledMaskTests.read
    run_code = CompiledMaskTests.run_code
    initialize = CompiledMaskTests.initialize

    def setUp(self):
        CompiledMaskTests.setUp(self)
        code, labels, rows = idle.build()
        self.labels.update(labels)
        self.rows.update({row['address']: row for row in rows})
        self.install(idle.CODE, code)
        self.assertEqual(self.initialize(), 201509)

    def check(self, masks, vectors, vector_address=0xa400, interrupt=None):
        encoded = transform(masks, 480, 4)
        flags = idle.idle_stripes(vectors, masks[:384])
        poison = bytes(v ^ 255 for v in masks)
        wanted = bytearray(masks)
        for stripe, skipped in enumerate(flags):
            if skipped: wanted[stripe*32:stripe*32+32] = poison[stripe*32:stripe*32+32]
        self.install(INPUT, encoded); self.install(vector_address, vectors)
        self.install(MASKS, poison); self.install(FLAGS, b'\xa5'*64)
        self.install(idle.IDLE_BASE+1, b'\xa5'*12)
        word(self.cpu, idle.VECTOR_POINTER, vector_address)
        self.cpu.set_hl(INPUT)
        outputs = [(FLAGS, FLAGS+64), (MASKS+384, MASKS+480), (idle.IDLE_BASE+1, idle.IDLE_BASE+13)]
        outputs += [(MASKS+i*32, MASKS+i*32+32) for i, skipped in enumerate(flags) if not skipped]
        ticks = self.run_code(self.labels['decode'], outputs, interrupt)
        self.assertEqual(ticks, idle.expected_tstates(encoded, vectors, vector_address=vector_address))
        self.assertEqual(self.read(MASKS, 480), bytes(wanted))
        self.assertEqual(self.read(idle.IDLE_BASE+1, 12), bytes(255*flag for flag in reversed(flags)))
        self.assertEqual(self.read(FLAGS+60, 4), bytes(4))
        self.assertEqual(self.read(vector_address, 192), vectors)
        self.assertEqual(self.read(INPUT, len(encoded)), encoded)
        self.assertEqual(self.cpu.hl(), INPUT+len(encoded))
        return ticks

    def test_all_group_patterns(self):
        for mask in range(256):
            source = bytes((i % 255 + 1) if mask & (128 >> (i % 8)) else 0 for i in range(480))
            with self.subTest(mask=mask): self.check(source, bytes(192))

    def test_each_vector_and_mask_can_prevent_skipping(self):
        for index in range(192):
            vectors = bytearray(192); vectors[index] = 81
            self.check(bytes(480), bytes(vectors), vector_address=0x9f93)
        for index in range(384):
            masks = bytearray(480); masks[index] = 128
            self.check(bytes(masks), bytes(192))

    def test_mixed_patterns_and_repeated_poison(self):
        rng = random.Random(4721)
        for _ in range(64):
            masks, vectors = bytearray(480), bytearray(192)
            for stripe in range(12):
                if rng.randrange(2):
                    masks[stripe*32:stripe*32+32] = bytes(rng.randrange(256) if rng.randrange(2) else 0 for _ in range(32))
                if rng.randrange(2): vectors[stripe*16+rng.randrange(16)] = rng.randrange(1, 89)
            masks[384:] = bytes(rng.randrange(256) if rng.randrange(2) else 0 for _ in range(96))
            self.check(bytes(masks), bytes(vectors))

    def test_real_ay_irq_after_every_instruction(self):
        import ay_interrupt
        import playback_schedule
        from build_zxv_trd import MiniAssembler
        from test_compiled_masks_z80 import STACK, STOP
        a = MiniAssembler(0x9400)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a,dos_irq=True,full_rom_clock=True,memory_clock=True,audio_irq=True)
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76)
        self.assertLess(a.pc,0x9800)
        self.install(0x9400,a.resolve())
        cpu = self.cpu; cpu.pc,cpu.sp = a.labels['setup_clock'],STACK
        cpu.push(STOP)
        while cpu.pc != STOP: cpu.step()
        cpu.write8(a.labels['audio_enabled'],1)
        names = ('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_b','alt_c',
                 'alt_d','alt_e','alt_h','alt_l','alt_z','alt_carry','port_7ffd','sp')
        calls = 0

        def interrupt(cpu):
            nonlocal calls
            allowed,cpu.allowed_writes = cpu.allowed_writes,None
            word(cpu,a.labels['audio_remaining'],65535)
            index = cpu.read8(a.labels['audio_read_index'])
            slot = ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
            for offset,value in enumerate((1,8,calls & 15)): cpu.write8(slot+offset,value)
            cpu.write8(a.labels['audio_write_index'],(index+1) & 31)
            saved = {name:getattr(cpu,name) for name in names}
            before,pc = cpu.tstates,cpu.pc
            cpu.push(pc); cpu.pc=0xbdbd; cpu.iff1=False; cpu.tstates+=19
            while cpu.pc != pc:
                self.assertNotEqual(cpu.pc,a.labels['fatal']); cpu.step()
            self.assertEqual(saved,{name:getattr(cpu,name) for name in names})
            self.assertEqual(cpu.ay[8],calls & 15)
            self.assertEqual(cpu.tstates-before,583)
            calls += 1
            self.assertEqual(word(cpu,a.labels['elapsed_fields']),calls & 65535)
            self.assertEqual(word(cpu,a.labels['audio_underruns']),0)
            cpu.allowed_writes = allowed
            return cpu.tstates-before

        for mask in (0,1,85,128,255):
            masks = bytes((i % 255+1) if mask & (128 >> (i % 8)) else 0 for i in range(480))
            vectors = bytes(81 if i in (16,47,191) else 0 for i in range(192))
            self.check(masks,vectors,interrupt=interrupt)
        self.assertGreater(calls,5000)


if __name__ == '__main__': unittest.main()
