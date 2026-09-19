import unittest

from frame_output_pipeline import Harness, INPUT, BITMAP
from frame_metadata_z80 import CODE, FLAGS, expected_tstates
from probe_motion_metadata import transform


class FrameMetadataTests(unittest.TestCase):
    def test_all_presence_patterns_and_exact_instruction_formula(self):
        h = Harness([bytes([8]*256)]*2, bytes(256), decode_metadata=True)
        cpu = h.cpu
        for flags in range(256):
            source = bytes((i % 255+1) if flags & (128 >> (i % 8)) else 0 for i in range(480))
            encoded = transform(source, 480, 4)
            cpu.guarding = False
            for i, value in enumerate(encoded):
                cpu.write8(INPUT+i, value)
            cpu.input_end = INPUT+len(encoded); cpu.set_hl(INPUT)
            result = h.execute(CODE)
            self.assertEqual(result['total_tstates'], expected_tstates(encoded))
            self.assertEqual(bytes(cpu.read8(BITMAP+i) for i in range(480)), source)
            self.assertEqual(bytes(cpu.read8(FLAGS+60+i) for i in range(4)), bytes(4))
            self.assertEqual(cpu.hl(), cpu.input_end)


if __name__ == '__main__':
    unittest.main()
