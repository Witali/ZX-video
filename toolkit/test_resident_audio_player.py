"""Resident service thresholds, exact fast-path costs and three-slot wrap."""
import unittest

from ay_huffman_stream import encode
from benchmark_resident_audio_z80 import Harness, REGISTERS
import pipelined_frame_z80 as video
from resident_audio_player import service, bank_helpers
from resident_audio_z80 import bridge


def fixture(records,*,batch=6):
    h=Harness(encode(records)[0],paging=True,batch=batch)
    c=h.cpu
    guard,labels,rows=service(h.audio,0)
    wrapper=bridge(labels['service']+len(guard),h.labels['fill'],page=video.PAGE,shadow=video.SHADOW)
    guard,labels,rows=service(h.audio,wrapper['origin'])
    for i,value in enumerate(guard+bytes.fromhex(wrapper['code_hex'])):
        c.write8(labels['service']+i,value)
    c.listing.update({r['address']:r for r in rows+wrapper['listing']})
    c.port_7ffd=0x17;c.write8(video.SHADOW,0x17)
    return h,labels


class ResidentAudioPlayerTests(unittest.TestCase):
    def test_all_occupancies_wrapped_indices_and_service_cycles(self):
        for read_index in (0,1,17,31):
            for occupancy in range(32):
                h,labels=fixture([b'\0']*60);c=h.cpu
                c.write8(h.audio['audio_read_index'],read_index)
                c.write8(h.audio['audio_write_index'],(read_index+occupancy)&31)
                before={name:getattr(c,name) for name in REGISTERS}
                elapsed=h.run('fill',{'fill':labels['service']})
                self.assertEqual({name:getattr(c,name) for name in REGISTERS},before)
                self.assertEqual(c.published,6 if occupancy<24 else 0)
                self.assertEqual(elapsed,108+436+4843 if occupancy<24 else 103)

    def test_service_real_ay_irq_after_each_instruction(self):
        records=[bytes([1,6,v]) if v%4 else b'\0' for v in range(48)]
        h,labels=fixture(records)
        while h.cpu.published<len(records):
            before={name:getattr(h.cpu,name) for name in REGISTERS}
            h.run('fill',{'fill':labels['service']},hook=h.interrupt)
            self.assertEqual({name:getattr(h.cpu,name) for name in REGISTERS},before)
        while h.consumed<len(records):h.consume()
        h.finish()
        self.assertGreater(h.cpu.irq_count,1000)

    def test_larger_batch_fills_available_space_and_keeps_irq_safe(self):
        h,labels=fixture([b'\0']*80,batch=31)
        self.assertEqual(h.run('fill',{'fill':labels['service']}),108+436+109+789*31)
        self.assertEqual(h.cpu.published,31)
        self.assertEqual(h.run('fill',{'fill':labels['service']}),103)
        for _ in range(10):h.consume()
        h.run('fill',{'fill':labels['service']})
        self.assertEqual(h.cpu.published,41)
        h,labels=fixture([bytes([1,6,v]) for v in range(64)],batch=31)
        while h.cpu.published<len(h.records):h.run('fill',{'fill':labels['service']},hook=h.interrupt)
        while h.consumed<len(h.records):h.consume()
        h.finish()

    def test_three_slot_advance_preserves_other_registers_and_timing(self):
        h=Harness(encode([])[0]);c=h.cpu;c.checking=False;c.port_7ffd=0x17
        code,labels,rows=bank_helpers(h.audio,{'phase':0xe150},0x941e)
        for i,v in enumerate(code):c.write8(0xdb20+i,v)
        for slot in range(3):
            c.a=slot
            before={name:getattr(c,name) for name in REGISTERS if name not in ('a','z','carry')}
            cost=h.run('advance_slot',labels,check=False)
            self.assertEqual(c.a,(slot+1)%3)
            self.assertEqual(cost,30 if slot==2 else 22)
            self.assertEqual({name:getattr(c,name) for name in before},before)


if __name__=='__main__':unittest.main()
