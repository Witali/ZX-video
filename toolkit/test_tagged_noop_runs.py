"""Run boundaries, ordinary fragment overhead and complete-frame equivalence."""
import unittest
from benchmark_context_huffman import word
from frame_output_pipeline import Harness, frames
from test_frame_output_pipeline import fixture
from probe_fast_noop_scan import scanner_tstates
import compact_cursor
import tagged_noop_runs as tags


def harness():
    h = Harness([bytes([8]*256)]*2, bytes(256), raw_attributes=True,
        fast_mask_dispatch=True, selective_cache=True, skip_noop_runs=True,
        fast_noop_scan=True, register_fragments=True)
    compact_cursor.install_stage(h)
    return h


class TaggedRunTests(unittest.TestCase):
    def test_each_run_and_vector_page_boundary(self):
        old, new = harness(), harness(); tags.install_stage(new)
        for offset in range(256):
            for length in range(1,17):
                for following in ('end', 'vector', 'patch'):
                    if length == 16 and following != 'end': continue
                    results = []
                    for tagged, h in enumerate((old,new)):
                        c = h.cpu; c.guarding = False
                        vector, masks = 0xa700+offset, 0xa4fe
                        for i in range(17): c.write8(vector+i, 0)
                        for i in range(34): c.write8(masks+i, 0)
                        if following == 'vector': c.write8(vector+length,81)
                        if following == 'patch': c.write8(masks+2*length+(offset&1),128)
                        if tagged: c.write8(vector,128+length)
                        word(c,h.recon['vectors'],vector); word(c,h.recon['bitmap_masks'],masks)
                        column = 16-length if following == 'end' else 0
                        word(c,h.recon['target'],0x6600+2*column)
                        left = length if following == 'end' else 16
                        c.write8(h.recon['tiles_left'],left)
                        c.sp=0xbb00; c.pc=h.recon['tile']; before=c.tstates
                        while True:
                            row=h.instructions[c.pc]; step=c.tstates; c.step()
                            ticks=row['tstates']
                            self.assertIn(c.tstates-step,ticks if isinstance(ticks,list) else [ticks])
                            if c.pc in (h.recon['tile'],h.recon['stripe_done']): break
                        wanted=(308 if following=='end' else 318) if tagged else scanner_tstates(length,following,True)-20
                        self.assertEqual(c.tstates-before,wanted)
                        self.assertEqual(c.sp,0xbb00)
                        results.append((word(c,h.recon['vectors']),word(c,h.recon['bitmap_masks']),
                            word(c,h.recon['target']),c.read8(h.recon['tiles_left'])))
                        self.assertEqual(results[-1],(vector+length,masks+2*length,0x6600+2*(column+length),left-length))
                    self.assertEqual(*results)

    def test_roundtrip_and_edges(self):
        vectors,masks=bytearray(192),bytearray(384)
        vectors[31]=85; masks[80]=128; masks[105]=1
        for minimum in range(1,17):
            tagged=tags.encode(bytes(vectors),bytes(masks),minimum)
            self.assertEqual(tagged[:16],vectors[:16]); self.assertEqual(tagged[176:],vectors[176:])
            self.assertEqual(tags.decode_vectors(tagged,bytes(masks),inplace=True)[0],vectors)

    def test_complete_frames_and_predicted_delta(self):
        states,stream,_=fixture(8); tables,mapping,packets=frames(stream)
        old,new=[Harness(tables,mapping,raw_attributes=True,fast_mask_dispatch=True,
            skip_noop_runs=True,skip_static_stripes=True,
            fast_noop_scan=True,register_fragments=True) for _ in range(2)]
        for h in (old,new): compact_cursor.install_stage(h)
        tags.install_stage(new)
        for i,((group,native),state) in enumerate(zip(packets,states)):
            before=old.run(group,native,state.tobytes(),i)
            tagged=(*group[:3],tags.encode(group[3],group[4]),*group[4:])
            after=new.run(tagged,native,state.tobytes(),i)
            self.assertEqual(after['total_tstates']-before['total_tstates'],
                             tags.cycle_counts(group[3],group[4])['delta_tstates'])

    def test_actual_irq_at_each_run_instruction(self):
        import ay_interrupt
        import pipelined_frame_z80 as video
        from pipelined_frame_harness import Clock
        from test_pipelined_frame import fixture as video_fixture
        for slow in (False,True):
            h,_,_=video_fixture(1,irq_safe_paging=True)
            ticks=[]; clock=Clock(h,ticks); c=h.cpu; c.guarding=False
            # This older synthetic fixture keeps its unused ZX0 routine in
            # the new helper's space. This test runs only tile/IRQ code.
            # The full frame stage and disk installer check real free RAM.
            for at in range(tags.CODE,tags.LIMIT): c.write8(at,0)
            report=tags.build(c.read8,h.instructions.values(),h.frame.recon)
            for at,key in ((tags.CODE,'code_hex'),(report['hook_address'],'hook_hex')):
                for i,value in enumerate(bytes.fromhex(report[key])): c.write8(at+i,value)
            word(c,0xbdbe,0xbd00 if slow else 0xbd80)
            c.write8(video.ENABLED,1); c.write8(video.READY,1); word(c,video.DEADLINE,0)
            c.write8(h.audio['audio_enabled'],1); calls=0
            for length in (1,4,16):
                for end in (False,True):
                    if length==16 and not end: continue
                    r=h.frame.recon; c.write8(0xa7ff,128+length)
                    word(c,r['vectors'],0xa7ff); word(c,r['bitmap_masks'],0xa4fe)
                    word(c,r['target'],0x6600); c.write8(r['tiles_left'],length if end else 16)
                    c.pc=r['tile']; saved_sp=c.sp
                    while True:
                        c.step()
                        tick=bytes([1,8,calls&15]); ticks.append(tick)
                        slot=c.read8(h.audio['audio_read_index'])
                        for i,b in enumerate(tick): c.write8(ay_interrupt.QUEUE_BASE+slot*32+i,b)
                        c.write8(h.audio['audio_write_index'],(slot+1)&31)
                        word(c,h.audio['audio_remaining'],65535)
                        clock.run_irq(); calls+=1
                        if c.pc in (r['tile'],r['stripe_done']): break
                    self.assertEqual(c.sp,saved_sp)
                    self.assertEqual((word(c,r['vectors']),word(c,r['bitmap_masks']),
                        word(c,r['target']),c.read8(r['tiles_left'])),
                        (0xa7ff+length,0xa4fe+2*length,0x6600+2*length,0 if end else 16-length))
            self.assertGreater(calls,100)
            self.assertEqual(c.read8(h.audio['audio_underruns']),0)


if __name__ == '__main__': unittest.main()
