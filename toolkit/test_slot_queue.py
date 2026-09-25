"""Execute the queue with real Z80 ownership/copying and mocked ROM reads."""
import unittest
from collections import Counter

from benchmark_context_huffman import word
from benchmark_bank_local_zx0 import STACK,STOP
from test_direct_slot_input import fixture,literal
from test_fap3_disk import install
from zx0_speed import Token,encode
import slot_queue_z80 as queue
import pipelined_frame_z80 as video


class QueueHarness:
    def __init__(self,h,blocks,*,partial_consumption=False):
        self.h=h;self.cpu=h.cpu;self.cpu.port_7ffd=0x17
        self.regions,self.q,rows=queue.build(h.decoder.labels,h.p,blocks,partial_consumption=partial_consumption)
        for address,blob in self.regions:install(self.cpu,address,blob)
        self.instructions=dict(h.instructions)
        self.instructions.update({r['address']:r for r in rows})
        self.histogram=Counter();self.calls=[]

    def call(self,entry):
        cpu=self.cpu;cpu.pc=entry;cpu.sp=STACK;cpu.push(STOP)
        start,steps=cpu.tstates,cpu.steps
        while cpu.pc!=STOP:
            if cpu.pc in (self.q['fatal'],self.h.p['fatal'],self.h.decoder.labels['fatal']):
                raise AssertionError('queue reached fatal')
            if cpu.steps-steps>4000000:raise AssertionError('queue failed to return')
            pc,before=cpu.pc,cpu.tstates;cpu.step();ticks=cpu.tstates-before
            row=self.instructions.get(pc)
            if row:
                expected=row['tstates']
                if ticks not in (expected if isinstance(expected,list) else [expected]):
                    raise AssertionError(('timing differs',hex(pc),ticks,row))
            elif not 0x7c00<=pc<self.h.decoder.labels['state']:
                raise AssertionError(('unknown instruction',hex(pc)))
            self.histogram[pc,ticks]+=1
        if cpu.sp!=STACK or cpu.port_7ffd&7!=7:raise AssertionError('queue stack/page differs')
        self.calls.append((entry,cpu.tstates-start))
        return cpu.tstates-start

    def take(self,count):
        self.cpu.set_bc(count);self.cpu.set_de(0xa6a0)
        self.call(self.q['take'])
        if self.cpu.de()!=0xa6a0+count:raise AssertionError('destination does not advance')
        return bytes(self.cpu.read8(0xa6a0+i) for i in range(count))


class QueueTests(unittest.TestCase):
    def test_idle_helper_return_after_publication_does_not_halt(self):
        from test_pipelined_frame import fixture as frame_fixture
        from pipelined_frame_harness import Clock
        h,_,ticks=frame_fixture(1,irq_safe_paging=True)
        clock=Clock(h,ticks,disk_idle_entry=0x6100)
        c=h.cpu;c.guarding=False;c.write8(video.READY,1)
        # Model an IRQ publishing inside the helper just before it reports
        # no work. Waiting for another IRQ would delay foreground progress.
        install(c,0x6100,bytes([0xaf,0x32,video.READY&255,video.READY>>8,0xc9]))
        for pc,ticks in ((0x6100,4),(0x6101,13),(0x6104,10)):
            h.instructions[pc]=dict(phase='schedule',tstates=ticks)
        before=c.halts
        h.execute(clock.labels['wait_published'])
        self.assertEqual(c.halts,before)

    def test_publication_without_legacy_history_state(self):
        from test_pipelined_frame import fixture as frame_fixture
        from pipelined_frame_harness import Clock
        costs=[]
        for legacy in (True,False):
            h,_,ticks=frame_fixture(1,irq_safe_paging=True);clock=Clock(h,ticks);c=h.cpu
            c.guarding=False
            if not legacy:
                regions,h.video,rows=video.build_video(h.frame.draw,{},h.audio,irq_safe_paging=True)
                h.instructions={pc:row for pc,row in h.instructions.items() if not video.VIDEO<=pc<video.PAGE}
                h.instructions.update({r['address']:r for r in rows})
                for address,blob in regions:install(c,address,blob)
            alias=h.z['history_page'];c.write8(alias,0xa5)
            c.write8(video.ENABLED,1);c.write8(video.READY,1)
            word(c,video.DEADLINE,0);word(c,h.audio['elapsed_fields'],0)
            c.pc=0x93f0
            costs.append(clock.run_irq())
            self.assertEqual(c.read8(alias),0xa5^8 if legacy else 0xa5)
            self.assertEqual(word(c,video.PUBLISHED),1)
        self.assertEqual(costs[0]-costs[1],33)

    def test_full_empty_wrap_partial_and_zero_consumption(self):
        repeated=bytes(range(256))*32
        blocks=[literal(17),(encode(repeated,[Token(0,256),Token(256,7936,256)]),repeated)]
        blocks += [literal(n) for n in (511,1,277,2048,14,700,80,1)]
        q=QueueHarness(fixture(blocks),len(blocks));c=q.cpu
        c.write8(video.SHADOW,0x1f)
        q.call(q.q['prefill']);self.assertEqual(c.read8(q.q['count']),4)
        before=[bytes(b) for b in c.banks];reads=len(c.reads)
        q.call(q.q['step']);self.assertEqual(c.a,0)
        self.assertEqual(reads,len(c.reads))
        self.assertEqual([bytes(c.banks[b]) for b in (0,1,3,4)],[before[b] for b in (0,1,3,4)])
        self.assertEqual(q.take(0),b'');self.assertEqual(c.read8(q.q['count']),4)
        expected=b''.join(raw for _,raw in blocks);out=bytearray()
        counts=(1,15,3,257,2047,4000,819,1,8,1777);i=0
        while len(out)<len(expected):
            # Populate ahead while a partial consumer slot remains in use.
            retained={b:bytes(c.banks[b][8192:]) for b in (0,1,3,4)}
            occupied=[(c.read8(q.q['read_slot'])+j)%4 for j in range(c.read8(q.q['count']))]
            q.call(q.q['step'])
            for slot in occupied:
                b=(0,1,3,4)[slot];self.assertEqual(bytes(c.banks[b][8192:]),retained[b])
            count=min(counts[i%len(counts)],len(expected)-len(out));i+=1
            out+=q.take(count)
            self.assertEqual(c.port_7ffd&8,8)
        self.assertEqual(bytes(out),expected)
        self.assertEqual(c.read8(q.q['count']),0)
        self.assertEqual(word(c,q.q['blocks_left']),0)
        q.call(q.q['step']);self.assertEqual(c.a,0)
        self.assertEqual([r['sector'] for r in c.reads],q.h.positions)
        with self.assertRaises(AssertionError):q.take(1)

    def test_shared_sector_with_more_blocks_than_slots(self):
        blocks=[literal(1)]*35
        q=QueueHarness(fixture(blocks,47),len(blocks))
        # Forced synchronous read spans every slot with no host refill.
        self.assertEqual(q.take(35),bytes(35))
        self.assertEqual([r['sector'] for r in q.cpu.reads],q.h.positions)
        self.assertEqual(q.cpu.read8(q.q['count']),0)


if __name__=='__main__':unittest.main()
