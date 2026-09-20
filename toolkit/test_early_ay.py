import struct
import unittest

from benchmark_context_huffman import word
from bulk_frame_stream import pack, read_packet
from bulk_frame_z80 import EARLY_AY_BYTES
from frame_output_pipeline import frames, display_screen
from frame_stream_harness import Harness
from pipelined_frame_harness import Clock
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from test_frame_stream_z80 import source, ring
from test_pipelined_frame import fixture


class EarlyAYTests(unittest.TestCase):
    def test_prefix_end_maximum_records_banked_input_and_exact_parser_delta(self):
        states,cells,fap1,_ = source(4)
        raw,_ = pack(fap1,stored_guards=False)
        r = Reader(raw); read_header(r,magic=b'FAP3'); header = raw[:r.pos]
        changed = bytearray(header); records=[]; packets=[]
        for index in range(4):
            _,detail = read_packet(r,stored_guards=False)
            counts = ([0]*6, [11]*6, [0,1,11,2,10,3], [11,0,7,8,2,0])[index]
            ticks = [bytes([n])+b''.join(bytes([reg,0]) for reg in range(n)) for n in counts]
            body = b''.join(ticks)+detail['payload'][sum(map(len,detail['ticks'])):]
            packets.append((len(changed),body)); records.extend(ticks)
            changed += struct.pack('<H',len(body))+body
        r.end(); tables,mapping,_ = frames(cells)
        for compressed,size in ((False,137),(True,509)):
            pair = [Harness(ring(changed,size,compressed),tables,mapping,4,bulk=True,
                zero_copy=True,stored_guards=False,ring_start=0xffff,unrolled_copy=True,
                early_ay=early) for early in (False,True)]
            for h in pair: h.consume_header(header)
            for index,(offset,body) in enumerate(packets):
                measured=[]
                for early,h in enumerate(pair):
                    enqueue_positions=[]
                    def observe(cpu):
                        if cpu.pc == h.audio['audio_enqueue_six']:
                            enqueue_positions.append((h.blocks-1)*size+word(cpu,h.r['position']))
                        return 0
                    measured.append(h.execute(h.p['next_frame'],interrupt=observe))
                    self.assertEqual(enqueue_positions,[offset+2+(EARLY_AY_BYTES if early else len(body))])
                    self.assertEqual(bytes(h.cpu.read8(0xa6a0+j) for j in range(len(body)+1)),body+b'\0')
                    self.assertEqual(bytes(h.cpu.banks[5][0x2400:0x3300]),states[index].tobytes())
                    h.publish(); h.drain_six(records[index*6:index*6+6])
                self.assertEqual(measured[1]['stages']['packet']-measured[0]['stages']['packet'],83)
                for stage in ('audio','metadata','reconstruct','output','handoff'):
                    self.assertEqual(measured[1]['stages'][stage],measured[0]['stages'][stage])
                for bank in (5,7): self.assertEqual(pair[0].cpu.banks[bank][:6912],pair[1].cpu.banks[bank][:6912])
            for h in pair: self.assertEqual(h.cpu.consumed,len(h.cpu.ring_data))

    def test_50hz_eof_both_screens_and_volume_bar(self):
        import disk_progress_z80 as progress
        for count in (1,2,3,8):
            for ahead in (False,'idle'):
                h,states,ticks = fixture(count,bar=True,packet_ahead=ahead,unrolled_copy=True,early_ay=True)
                checked=dict(compact=0,native=0,publish=0)
                if ahead: checked['packet']=0
                def observe(kind,clock):
                    i=checked[kind]; cpu=h.cpu
                    if kind=='compact':
                        self.assertEqual(bytes(cpu.banks[5][0x2400:0x3300]),states[i].tobytes())
                    if kind in ('native','publish'):
                        expected=progress.reference_screen(display_screen(states[i].tobytes(),black_borders=True),
                            checked['publish'] if kind=='native' else i,count)
                        self.assertEqual(bytes(cpu.banks[7 if i%2==0 else 5][:6912]),expected)
                    checked[kind]+=1
                clock=Clock(h,ticks,lookahead=True,observer=observe)
                clock.prime(); clock.start()
                for _ in range(1,count): clock.play_one()
                clock.drain()
                self.assertEqual(checked,dict.fromkeys(checked,count))
                self.assertEqual(clock.ticks,6*count)
                self.assertFalse(any(p['late_fields'] for p in clock.publications))
                self.assertEqual(h.cpu.consumed,len(h.cpu.ring_data))
                self.assertEqual(bytes(h.cpu.banks[5][0x1b00:0x2400]),b'\xa5'*0x900)
                self.assertLessEqual(h.p['end'],progress.CODE)

    def test_invalid_audio_count_and_packet_lengths_rejected(self):
        _,cells,fap1,_=source(1); raw,rows=pack(fap1,stored_guards=False)
        tables,mapping,_=frames(cells); offset=rows[0]['offset']
        bads=[]
        for size in (0,137,293,4704,65535):
            data=bytearray(raw); struct.pack_into('<H',data,offset,size); bads.append(data)
        data=bytearray(raw); data[offset+2]=12; bads.append(data)
        for data in bads:
            h=Harness(ring(data),tables,mapping,1,bulk=True,stored_guards=False,early_ay=True)
            h.consume_header(data[:offset])
            with self.assertRaises((AssertionError,RuntimeError)): h.prepare()
            self.assertFalse(any(h.cpu.banks[5][:6912])); self.assertFalse(any(h.cpu.banks[7][:6912]))


if __name__=='__main__': unittest.main()
