import unittest

import cell_output_stream as cell
import probe_fast_fragments as fast
import probe_fragment_channels as channels
import test_fast_fragments as fixtures
from test_hybrid_tiles import header


class CellOutputStreamTests(unittest.TestCase):
    def test_group_limits_maps_and_original_stream_roundtrip(self):
        states, vectors, residual, selected = fixtures.FastFragmentTests().fixture(9)
        maps = bytes(range(240))*3
        for invalid in (0, 9, 1.5):
            with self.assertRaises(ValueError):
                fast.encode(header(9), states, vectors, residual, bytes(256),
                    [bytes([8]*256)]*2, selected, group_frames=invalid)
        for group_frames in (1, 8):
            intermediate, _ = fast.encode(header(9), states, vectors, residual,
                bytes(256), [bytes([8]*256)]*2, selected, group_frames=group_frames)
            source, _ = channels.split(intermediate, states, vectors, residual)
            data = cell.pack(source, maps)
            rebuilt, actual, groups = cell.unpack(data)
            self.assertEqual(rebuilt, source)
            self.assertEqual(actual, maps)
            self.assertEqual(channels.restore(rebuilt)[1], states.tobytes())
            self.assertTrue(all(g['frames'] <= group_frames for g in groups))
            if group_frames == 1:
                self.assertEqual(len(groups), 9)
            for invalid in (data[:-1], data+b'!', b'FSF1'+data[4:]):
                with self.assertRaises(ValueError):
                    cell.unpack(invalid)
            with self.assertRaises(ValueError):
                cell.pack(source, maps[:-1])


if __name__ == '__main__':
    unittest.main()
