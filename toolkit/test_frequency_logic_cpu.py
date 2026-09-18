"""Independent opcode checks needed by the fixed-alphabet Z80 experiment."""
import unittest

from validate_fast_sparse import CPU


class FrequencyCPUInstructionTests(unittest.TestCase):
    def test_cpl_preserves_modeled_flags(self):
        cpu = CPU(b'', b'')
        cpu.write8(0x8000, 0x2f)
        for value in range(256):
            for z in (False, True):
                for carry in (False, True):
                    cpu.a, cpu.z, cpu.carry, cpu.pc = value, z, carry, 0x8000
                    before = cpu.tstates
                    cpu.step()
                    self.assertEqual((cpu.a, cpu.z, cpu.carry, cpu.tstates-before),
                                     (255-value, z, carry, 4))

    def test_circular_rotates_registers_and_memory(self):
        cpu = CPU(b'', b'')
        for right in (False, True):
            for register in range(8):
                cpu.write8(0x8000, 0xcb)
                cpu.write8(0x8001, register + (8 if right else 0))
                for value in range(256):
                    for carry in (False, True):
                        cpu.set_hl(0xa400)
                        cpu.put(register, value)
                        cpu.pc, cpu.carry = 0x8000, carry
                        before = cpu.tstates
                        cpu.step()
                        bits = f'{value:08b}'
                        expected = int(bits[-1]+bits[:-1] if right else bits[1:]+bits[0], 2)
                        out_carry = bits[-1 if right else 0] == '1'
                        self.assertEqual(cpu.reg(register), expected)
                        self.assertEqual((cpu.z, cpu.carry, cpu.tstates-before),
                                         (expected == 0, out_carry, 15 if register == 6 else 8))


if __name__ == '__main__':
    unittest.main()
