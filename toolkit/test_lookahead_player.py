"""Real FAP3 range checks and in-place decoding with a read-only second guard."""
import struct
import unittest
from unittest.mock import patch

import frame_output_pipeline as pipeline
import frame_stream_harness as stream
import cached_huffman_lookahead as cache
from bulk_frame_stream import pack
from bulk_frame_z80 import LENGTH
from frame_output_pipeline import frames
from lookahead_player import packet_contract, audit_packets
from build_fap3_trd import sha
from test_frame_stream_z80 import source, ring


class TwoGuardCPU(stream.FrameStreamCPU):
    second_guard_reads = 0

    def read8(self, address):
        if (self.guarding and self.phase == 'reconstruct'
                and address == self.packet_end+1
                and pipeline.INPUT <= address < pipeline.INPUT_END):
            self.second_guard_reads += 1
            previous = self.input_end
            self.input_end = self.packet_end+2
            try: return super().read8(address)
            finally: self.input_end = previous
        return super().read8(address)


def install(h):
    h.cpu.guarding = False
    contract = packet_contract(h.cpu.read8, h.instructions.values(),
                              dict(h.p, read_packet=h.p['next_frame']))
    report = cache.build(h.cpu.read8, h.instructions.values(), h.frame.recon, frame=True)
    for r in report['regions']+[contract]:
        for i, value in enumerate(bytes.fromhex(r['code_hex'])):
            h.cpu.write8(r['address']+i, value)
    h.instructions = {r['address']: r for r in report['listing']}
    return contract


class LookaheadPlayerTests(unittest.TestCase):
    def make(self, raw, tables, mapping, count, new):
        with patch.object(stream, 'FrameStreamCPU', TwoGuardCPU if new else stream.FrameStreamCPU):
            h = stream.Harness(ring(raw,509,True),tables,mapping,count,bulk=True,
                zero_copy=True,stored_guards=False,carry_huffman=True,
                cached_huffman_byte=True,register_fragments=True)
        if new: install(h)
        return h

    def test_real_length_check_accepts_two_readable_guards(self):
        _,cells,fap1,_ = source(1)
        raw,_ = pack(fap1,stored_guards=False)
        tables,mapping,_ = frames(cells)
        for new in (False,True):
            h = self.make(raw,tables,mapping,1,new)
            rows = [r for r in h.instructions.values() if h.p['next_frame'] <= r['address'] < h.p['video_payload_ready']]
            start = next(r['address'] for r in rows if r['instruction']=='LD HL,(length)')
            end = next(r['address'] for r in rows if r['instruction']=='LD DE,packet')
            c = h.cpu
            for size in (0,1,293,294,295,4701,4702,4703,4704,65535):
                c.guarding = False
                c.write8(LENGTH,size&255); c.write8(LENGTH+1,size>>8)
                c.pc = start
                before = c.tstates
                for _ in range(10):
                    if c.pc in (end,h.z['fatal']): break
                    c.step()
                accepted = 294 <= size <= (4702 if new else 4703)
                self.assertEqual(c.pc, end if accepted else h.z['fatal'])
                self.assertEqual(c.tstates-before, 94 if size>=294 else 55)

    def test_in_place_packets_keep_pixels_audio_and_parser_cycles(self):
        states,cells,fap1,ticks = source(4)
        raw,rows = pack(fap1,stored_guards=False)
        tables,mapping,_ = frames(cells)
        old,new = [self.make(raw,tables,mapping,4,option) for option in (False,True)]
        for h in (old,new): h.consume_header(raw[:rows[0]['offset']])
        for index,state in enumerate(states):
            second = pipeline.INPUT+rows[index]['payload_bytes']+1
            new.cpu.write8(second,0xa5 if index%2 else 0x3c)
            before,after = old.prepare(),new.prepare()
            self.assertEqual(after['stages']['packet'],before['stages']['packet'])
            self.assertEqual(new.cpu.read8(second),0xa5 if index%2 else 0x3c)
            for h in (old,new):
                h.publish(); h.drain_six(ticks[6*index:6*index+6])
                self.assertEqual(bytes(h.cpu.read8(0x6400+i) for i in range(3840)),state.tobytes())
            for bank in (5,7): self.assertEqual(old.cpu.banks[bank][:6912],new.cpu.banks[bank][:6912])
        self.assertEqual(new.cpu.consumed,len(new.cpu.ring_data))

    def test_empty_input_reads_arbitrary_second_guard_without_writing_it(self):
        _,cells,fap1,_ = source(1)
        raw,rows = pack(fap1,stored_guards=False)
        # Six unchanged AY ticks, flags, mask/coded lengths, cache, vectors,
        # eight zero group flags and an empty native update map.
        body = bytes(6)+struct.pack('<BHH',0,8,0)+bytes(3+192+8+80)
        self.assertEqual(len(body),294)
        raw = raw[:rows[0]['offset']]+struct.pack('<H',len(body))+body
        tables,mapping,_ = frames(cells)
        for poison in (0,0xa5,0x3c,255):
            h = self.make(raw,tables,mapping,1,True)
            h.consume_header(raw[:rows[0]['offset']])
            at = pipeline.INPUT+len(body)+1
            h.cpu.write8(at,poison)
            h.prepare(); h.publish(); h.drain_six([bytes(1)]*6)
            self.assertGreater(h.cpu.second_guard_reads,0)
            self.assertEqual(h.cpu.read8(at),poison)
            self.assertFalse(any(h.cpu.read8(0x6400+i) for i in range(3840)))

    def test_build_rejects_oversized_optional_packet(self):
        _,cells,fap1,_ = source(1)
        raw,rows = pack(fap1,stored_guards=False)
        at = rows[0]['offset']
        body = raw[at+2:]+bytes(4703-rows[0]['payload_bytes'])
        raw = raw[:at]+struct.pack('<H',len(body))+body
        with self.assertRaisesRegex(ValueError,'smaller packet'):
            audit_packets(raw,dict(raw_sha256=sha(raw),frame_start=0,frame_end_exclusive=1,frames=1))


if __name__ == '__main__': unittest.main()
