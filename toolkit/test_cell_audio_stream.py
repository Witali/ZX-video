import unittest

from cell_audio_stream import pack, unpack, take_tick
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from test_frame_output_pipeline import fixture


class CellAudioStreamTests(unittest.TestCase):
    def test_frame_alignment_and_exact_audio_and_video(self):
        _, cells, _ = fixture(3)
        records = [bytes([11])+b''.join(bytes([r, r]) for r in range(11))]
        records += [bytes([1, 6, tick & 31]) if tick % 2 else b'\0' for tick in range(1, 18)]
        audio = b''.join(records)
        data = pack(cells, audio)
        video, sound, sizes = unpack(data)
        self.assertEqual((video, sound), (cells, audio))
        self.assertEqual(sizes, [sum(map(len, records[i:i+6])) for i in range(0, 18, 6)])
        self.assertEqual(len(data), len(cells)+len(audio))
        for bad in (data[:-1], data+b'!', b'FSC1'+data[4:]):
            with self.assertRaises(ValueError):
                unpack(bad)
        for bad_audio in (audio[:-1], audio+b'\0'):
            with self.assertRaises(ValueError):
                pack(cells, bad_audio)
        r = Reader(data); read_header(r, magic=b'FSA1')
        corrupt = bytearray(data); corrupt[r.pos] = 12
        with self.assertRaisesRegex(ValueError, 'register count'):
            unpack(bytes(corrupt))

    def test_invalid_ay_register_records(self):
        for data in (bytes([1, 11, 0]), bytes([2, 3, 0, 3, 1]), bytes([2, 7, 0, 1, 0])):
            with self.assertRaisesRegex(ValueError, 'AY registers'):
                take_tick(Reader(data))


if __name__ == '__main__':
    unittest.main()
