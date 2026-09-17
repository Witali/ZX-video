"""Lossless prototype commands cover all periods, volumes and noise colours."""
import random
import unittest

import ay_events
import build_long_video_trd as video


class EventTests(unittest.TestCase):
    def test_roundtrip_table_and_literal_periods(self):
        rng=random.Random(50)
        frames=[video.AyFrame((p,p,p),(i%16,(i+1)%16,(i+2)%16),i%32)
                for i,p in enumerate(ay_events.PERIODS)]
        frames.append(video.AyFrame((0,0,0),(0,0,0),0))
        frames.extend(video.AyFrame(tuple(rng.randrange(4096) for _ in range(3)),
                                   tuple(rng.randrange(16) for _ in range(3)),rng.randrange(32)) for _ in range(1000))
        frames.extend([frames[-1]]*6)
        records=ay_events.encode_ticks(frames)
        self.assertEqual(ay_events.decode_ticks(b''.join(records),len(frames)),frames)
        self.assertEqual(records[-6:],[b'\0']*6)

    def test_invalid_or_incomplete_stream_is_rejected(self):
        for data,count in ((b'\0',1),(b'\x08',1),(b'\x01\x3f',1),(b'\x01\x3e\x00',1)):
            with self.assertRaises(ValueError):ay_events.decode_ticks(data,count)
        frames=[video.AyFrame((1,300,500),(0,12,15),31)]
        encoded=b''.join(ay_events.encode_ticks(frames))
        with self.assertRaises(ValueError):ay_events.decode_ticks(encoded+b'\0',1)
        with self.assertRaises(ValueError):ay_events.encode_ticks([video.AyFrame((4096,1,1),(0,0,0))])


if __name__=='__main__':unittest.main()
