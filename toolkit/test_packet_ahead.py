import json
from pathlib import Path
import unittest

from benchmark_context_huffman import word
from frame_output_pipeline import display_screen
from pipelined_frame_harness import Clock
import disk_progress_z80 as progress
import pipelined_frame_z80 as machine
from test_pipelined_frame import fixture


class PacketAheadTests(unittest.TestCase):
    def test_small_volumes_keep_masks_audio_eof_and_progress(self):
        self.exercise(True)

    def test_idle_prefetch_keeps_masks_audio_eof_and_progress(self):
        self.exercise('idle')

    def exercise(self,policy):
        for count in (1,2,3,8):
            for lookahead in (False,True):
                h,states,ticks=fixture(count,bar=True,packet_ahead=policy)
                checked=dict(packet=0,compact=0,native=0,publish=0)
                masks=[]
                def observe(kind,c):
                    i=checked[kind]; cpu=h.cpu
                    if kind=='packet':
                        if masks: self.assertEqual(bytes(cpu.read8(0xbf20+j) for j in range(80)),masks[-1])
                    elif kind=='compact':
                        self.assertEqual(bytes(cpu.banks[5][0x2400:0x3300]),states[i].tobytes())
                        source=word(cpu,h.frame.w['native_pointer'])
                        masks.append(bytes(cpu.read8(source+j) for j in range(80)))
                        self.assertEqual(bytes(cpu.read8(0xbf20+j) for j in range(80)),masks[-1])
                    else:
                        bank=7 if i%2==0 else 5
                        expected=progress.reference_screen(display_screen(states[i].tobytes(),black_borders=True),
                            checked['publish'] if kind=='native' else i,count)
                        self.assertEqual(bytes(cpu.banks[bank][:6912]),expected)
                    checked[kind]+=1
                clock=Clock(h,ticks,lookahead=lookahead,observer=observe)
                clock.prime()
                self.assertEqual(checked,dict(packet=min(3,count),compact=min(2,count),native=1,publish=0))
                clock.start()
                for _ in range(1,count): clock.play_one()
                clock.drain()
                self.assertEqual(checked,dict.fromkeys(checked,count))
                self.assertEqual(h.cpu.consumed,len(h.cpu.ring_data))
                self.assertEqual(clock.ticks,count*6)
                self.assertFalse(any(r['late_fields'] for r in clock.publications))
                self.assertEqual(word(h.cpu,machine.PUBLISHED),count)
                for bank in (5,7):
                    for row in progress.PIXEL_ROWS:
                        self.assertEqual(bytes(h.cpu.banks[bank][row-0x4000:row-0x4000+32]),b'\xff'*32)

    def test_default_pipeline_keeps_recorded_regions(self):
        old=json.loads(Path(__file__).with_name('pipelined_frame_cpu.json').read_text(encoding='utf-8'))
        h,_,ticks=fixture(8); c=Clock(h,ticks,lookahead=True)
        expected={r['base']:bytes.fromhex(r['code_hex']) for r in old['code_regions']}
        for address,code in h.regions:
            if address==machine.CODE:
                # The volume count is an explicit build-time parameter.
                modified=bytearray(expected[address]); offset=c.labels['remaining']-address
                modified[offset:offset+2]=(7).to_bytes(2,'little')
                self.assertEqual(code,modified)
            elif address not in (0xdc00,0x7f00):
                # The tiny fixture does not enable static-stripe reconstruction,
                # so wrapper operand addresses can differ; all other areas match.
                self.assertEqual(code,expected[address])


if __name__=='__main__': unittest.main()
