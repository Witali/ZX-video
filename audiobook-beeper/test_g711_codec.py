"""G.711 sign, silence, extrema and compact-table invariants."""
import unittest
import numpy as np
from g711_codec import decode,decode_table,encode


class G711(unittest.TestCase):
    def test_standard_silence_sign_and_extrema(self):
        np.testing.assert_array_equal(decode(bytes([255,127,128,0]),'mulaw'),[0,0,32124,-32124])
        np.testing.assert_array_equal(decode(bytes([0xd5,0x55,0xaa,0x2a]),'alaw'),[8,-8,32256,-32256])

    def test_readonly_word_tables_and_one_byte_input(self):
        for law in ('mulaw','alaw'):
            table=decode_table(law)
            self.assertEqual(table.nbytes,512);self.assertFalse(table.flags.writeable)
            self.assertEqual(len(decode(bytes(range(256)),law)),256)

    def test_invalid_inputs_are_rejected_before_external_encoding(self):
        for samples in ([32768],[-32769],[.1],[[0]]):
            with self.assertRaises(ValueError):encode(np.asarray(samples),'mulaw','unused-ffmpeg')
        with self.assertRaises(ValueError):decode_table('unknown')


if __name__=='__main__':unittest.main()
