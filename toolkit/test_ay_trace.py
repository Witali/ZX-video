"""Reject incomplete, reordered or wrong-stream emulator evidence."""
import copy
import hashlib
import unittest

import ay_interrupt
import build_long_video_trd as video
import verify_ay_trace as trace


def fixture():
    frames=[video.AyFrame((300,400,500),(10,12,14))]*6
    records=ay_interrupt.encode_ticks(frames)
    writes=[];ticks=[]
    for i,record in enumerate(records):
        writes.extend(dict(tstate=i*70000+j*83,register=r,value=v)
                      for j,(r,v) in enumerate(zip(record[1::2],record[2::2])))
        ticks.append(i*70000+1000)
    timing=[dict(audio_ticks=ticks,audio_writes=writes,clock_hz=3500000)]
    raw=b''.join(f.serialize() for f in frames)
    metadata=dict(frames=1,audio_source=dict(sha256=hashlib.sha256(raw).hexdigest()),
                  volumes=[dict(frame_start=0,frame_end=1)])
    return metadata,timing,raw


class TraceTests(unittest.TestCase):
    def test_complete_trace(self):
        result=trace.verify_build(*fixture())
        self.assertEqual(result['ticks'],6)
        self.assertEqual(result['volumes'][0]['unchanged_ticks_without_io'],5)

    def test_reject_incomplete_or_wrong_source(self):
        meta,timing,raw=fixture()
        for m,t,r in ((meta,[],raw),(meta,timing*2,raw),(meta,timing,raw[:-1]),
                      (meta,timing,bytes([raw[0]^1])+raw[1:])):
            with self.assertRaises(AssertionError):trace.verify_build(m,t,r)

    def test_reject_missing_extra_and_reordered_writes(self):
        meta,timing,raw=fixture()
        for kind in ('missing','extra','reordered','tick'):
            changed=copy.deepcopy(timing);writes=changed[0]['audio_writes']
            if kind=='missing':writes.pop()
            elif kind=='extra':writes.append(dict(tstate=1000000,register=8,value=10))
            elif kind=='reordered':writes[0],writes[1]=writes[1],writes[0]
            else:changed[0]['audio_ticks'].pop()
            with self.assertRaises(AssertionError):trace.verify_build(meta,changed,raw)


if __name__=='__main__':unittest.main()
