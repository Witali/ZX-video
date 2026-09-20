import unittest
import struct

from benchmark_context_huffman import word
from bulk_frame_stream import pack
from frame_output_pipeline import frames,display_screen
from frame_stream_harness import Harness
from pipelined_frame_harness import Clock,FIELD
import pipelined_frame_z80 as machine
import disk_progress_z80 as progress
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from test_frame_stream_z80 import source,ring


def fixture(count,*,bar=False,compressed=True,packet_ahead=False,unrolled_copy=False):
    states,cells,fap1,ticks=source(count,constant_attribute_borders=True)
    # A valid, easy schedule: retain the first reconstructed picture, copy it
    # once to the other native screen, then leave both unchanged. Heavy random
    # fixtures exceed the frame budget; those belong in measured failure runs.
    r=Reader(fap1); read_header(r,magic=b'FAP1')
    for _ in range(6): r.take(2*r.take(1)[0])
    _,ml,coded,lit=struct.unpack('<BHHH',r.take(7)); r.take(3+192+ml+80+coded+lit)
    fap1=fap1[:r.pos]+b''.join(b''.join(ticks[i*6:i*6+6])+struct.pack('<BHHH',0,8,0,0)
        +bytes(3+192+8)+(b'\xff'*80 if i==1 else bytes(80)) for i in range(1,count))
    states=states[:1].repeat(count,axis=0)
    raw,_=pack(fap1,stored_guards=False)
    tables,mapping,packets=frames(cells); cursor=Reader(raw); read_header(cursor,magic=b'FAP3')
    h=Harness(ring(raw,509,compressed),tables,mapping,count,bulk=True,zero_copy=True,
        stored_guards=False,skip_noop_runs=True,constant_attribute_borders=True,
        skip_black_borders=True,token_boundaries=True,pipelined=True,
        progress_frames=count if bar else None,packet_ahead=packet_ahead,unrolled_copy=unrolled_copy)
    h.consume_header(raw[:cursor.pos])
    return h,states,ticks


class PipelinedFrameTests(unittest.TestCase):
    def test_native_compact_overlap_exact_screens_ay_and_volume_bar(self):
        for count in (1,2,8):
            for lookahead in (False,True):
                h,states,ticks=fixture(count,bar=True)
                checked=dict(compact=0,native=0,publish=0)
                def observe(kind,clock):
                    i=checked[kind]; cpu=h.cpu
                    if kind=='compact':
                        self.assertEqual(bytes(cpu.banks[5][0x2400:0x3300]),states[i].tobytes())
                    else:
                        bank=7 if i%2==0 else 5
                        expected=progress.reference_screen(display_screen(states[i].tobytes(),black_borders=True),
                            checked['publish'] if kind=='native' else i,count)
                        self.assertEqual(bytes(cpu.banks[bank][:6912]),expected)
                        if kind=='publish': self.assertEqual(7 if cpu.port_7ffd&8 else 5,bank)
                    checked[kind]+=1
                clock=Clock(h,ticks,lookahead=lookahead,observer=observe)
                clock.prime()
                self.assertEqual(checked,dict(compact=min(2,count),native=1,publish=0))
                clock.start()
                for _ in range(1,count): clock.play_one()
                clock.drain()
                self.assertEqual(checked,dict(compact=count,native=count,publish=count))
                self.assertEqual(clock.ticks,6*count)
                self.assertEqual(h.cpu.consumed,len(h.cpu.ring_data))
                self.assertEqual(word(h.cpu,machine.PUBLISHED),count)
                self.assertEqual([r['audio_ticks'] for r in clock.publications],list(range(0,6*count,6)))
                self.assertFalse(any(r['late_fields'] for r in clock.publications))
                phase=[r['tstates']-clock.publications[0]['tstates']-i*6*FIELD
                    for i,r in enumerate(clock.publications)]
                self.assertLessEqual(max(phase)-min(phase),100)
                for bank in (5,7):
                    for row in progress.PIXEL_ROWS:
                        self.assertEqual(bytes(h.cpu.banks[bank][row-0x4000:row-0x4000+32]),b'\xff'*32)
                self.assertEqual(bytes(h.cpu.banks[5][0x1b00:0x2400]),b'\xa5'*0x900)

    def test_stale_foreground_page_cannot_revert_irq_publication(self):
        # A was loaded by the caller before an IRQ. The helper must merge the
        # latest display bit, for every possible ring/table/history bank.
        from stream_reader_harness import STACK,STOP
        for bank in (0,1,3,4,6,7):
            h,_,ticks=fixture(1); c=Clock(h,ticks); cpu=h.cpu
            cpu.guarding=False; cpu.write8(machine.ENABLED,1); cpu.write8(machine.READY,1)
            cpu.a=0x10|bank; cpu.pc=machine.PAGE; cpu.sp=STACK
            cpu.push(STOP); cpu.guarding=True
            c.run_irq()  # Turns on screen 7, preserving the stale requested A.
            self.assertEqual(cpu.a,0x10|bank)
            start=cpu.tstates
            while cpu.pc!=STOP:
                cpu.phase='paging'; cpu.step()
            self.assertEqual(cpu.tstates-start,88)
            self.assertEqual(cpu.port_7ffd,0x18|bank)
            self.assertEqual(cpu.read8(machine.SHADOW),0x18|bank)
            self.assertEqual(cpu.sp,STACK)

    def test_ready_deadline_and_absolute_recovery(self):
        # Feed a completed native screen by setting READY, exercising just the
        # real ISR. Miss one deadline, then recover the original six-field grid.
        h,_,ticks=fixture(1); c=Clock(h,ticks); cpu=h.cpu
        with self.assertRaises(ValueError): h.prepare()
        with self.assertRaises(ValueError): h.publish()
        cpu.guarding=False; cpu.write8(machine.ENABLED,1)
        word(cpu,machine.DEADLINE,7)
        for elapsed in range(1,26):
            word(cpu,h.audio['elapsed_fields'],elapsed-1)
            if elapsed in (8,9,20): cpu.write8(machine.READY,1)
            cpu.pc=0x93f0; cpu.guarding=True; c.run_irq(); cpu.guarding=False
        self.assertEqual([r['fields'] for r in c.publications],[8,13,20])
        self.assertEqual([r['late_fields'] for r in c.publications],[1,0,1])
        self.assertEqual(word(cpu,machine.DEADLINE),25)
        # The comparison also works when the u16 field counter wraps.
        cpu.write8(machine.READY,1); word(cpu,machine.DEADLINE,2)
        for elapsed in (65534,65535,0,1,2):
            word(cpu,h.audio['elapsed_fields'],(elapsed-1)&65535)
            c.run_irq()
        self.assertEqual(c.publications[-1]['fields'],2)
        self.assertEqual(word(cpu,machine.DEADLINE),8)

    def test_irq_costs_against_previous_audio_only_handler(self):
        # AF/BC/DE are saved by video_tick, HL by the existing outer clock.
        # All four branches are instruction-table sums, in addition to the
        # unchanged 191-T fast IRQ with audio disabled.
        h,_,ticks=fixture(1); c=Clock(h,ticks); cpu=h.cpu
        for enabled,ready,deadline,wanted in ((0,0,0,58),(1,0,0,85),(1,1,100,179),(1,1,0,478)):
            cpu.guarding=False; cpu.pc=0x93f0
            cpu.write8(machine.ENABLED,enabled); cpu.write8(machine.READY,ready)
            word(cpu,machine.DEADLINE,deadline)
            self.assertEqual(c.run_irq(),191+17+wanted)

    def test_timing_fixture_preserves_existing_default_machine_code(self):
        import json
        from pathlib import Path
        old=json.loads(Path(__file__).with_name('token_boundary_fast_clock_cpu.json').read_text(encoding='utf-8'))
        states,cells,fap1,_=source(1,constant_attribute_borders=True)
        tables,mapping,_=frames(cells); raw,_=pack(fap1,stored_guards=False)
        h=Harness(ring(raw),tables,mapping,1,bulk=True,zero_copy=True,stored_guards=False,
            skip_noop_runs=True,constant_attribute_borders=True,skip_black_borders=True,
            skip_static_stripes=True,token_boundaries=True)
        recorded={r['base']:bytes.fromhex(r['code_hex']) for r in old['code_regions']}
        for address,code in h.regions: self.assertEqual(code,recorded[address])
        self.assertEqual(h.z,old['decoder_labels'])


if __name__=='__main__': unittest.main()
