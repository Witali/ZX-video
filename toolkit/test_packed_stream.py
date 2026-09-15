"""Boundary and instruction-level regression tests for byte-contiguous frames."""
import random
from pathlib import Path
import tempfile
import unittest

import build_fast_sparse_trd as codec
import packed_stream
from validate_fast_sparse import validate_volume


class PackedStreamTests(unittest.TestCase):
    def execute(self, states):
        ay = [bytes((i % 256, 0, 0, 0, 0, 0, i % 16, 0, 0)) for i in range(len(states))]
        end, packets = codec.make_volume_packets(states, ay, 0, 2530, packed=True)
        self.assertEqual(end, len(states))
        video = codec.serialize_volume(packets, 25/3, packed=True)
        boot = codec.streaming.build_boot_basic()
        provisional, _ = codec.build_player(0, 0, packed=True)
        files = [codec.base.TrdFile('boot', 'B', boot, basic_variables_offset=len(boot), autostart_line=10),
                 codec.base.TrdFile('PLAYER', 'C', provisional, start=0x6000)]
        track, sector = codec.streaming.calculate_file_start(files)
        player, labels = codec.build_player(track, sector, packed=True)
        files[1] = codec.base.TrdFile('PLAYER', 'C', player, start=0x6000)
        files.append(codec.base.TrdFile('VIDEO', 'C', video, start=0))
        trd, _, _ = codec.streaming.place_files(files, 'TEST')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.trd'
            path.write_bytes(trd)
            result = validate_volume(path, labels, states, ay)
        self.assertEqual(result['frames'], len(states))
        self.assertEqual(result['disk_bytes'], len(video))
        self.assertGreaterEqual(result['minimum_sp'], 0x5F00)
        return packets

    def test_headers_at_every_sector_offset_and_banked_input(self):
        states = [bytes(((i//2) & 1,)) + bytes(3839) for i in range(1000)]
        packets = self.execute(states)
        position = 0
        offsets = set()
        for packet in packets:
            offsets.add(position % 256)
            position += len(packed_stream.frame_bytes(packet))
        self.assertEqual(offsets, set(range(256)))
        self.assertGreater(position, 32*256)

    def test_dense_scene_cuts_and_all_attribute_positions(self):
        rng = random.Random(128)
        states = [rng.randbytes(3840) for _ in range(4)]
        packets = self.execute(states)
        self.assertTrue(all(len(packed_stream.frame_bytes(p)) > 4096 for p in packets))

    def test_shared_sector_is_not_released_early(self):
        # All frames fit in one sector. The producer must not be asked for a
        # nonexistent sector just because another frame begins in that sector.
        self.assertEqual(packed_stream.minimum_startup_backlog([12]*10), 1)
        self.assertEqual(packed_stream.sector_demands([12]*10), [1]+[0]*9)
        self.execute([bytes(3840)]*10)

    def test_reject_missing_end_marker(self):
        with self.assertRaises(ValueError):
            packed_stream.sector_records(bytes((8, 0))*128, False)


if __name__ == '__main__': unittest.main()
