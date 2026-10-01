"""Sector cache ordering, wrap, bounds, paging and independent Z80 hit cycles."""
import unittest
from z80 import Z80Machine

from build_row_lzsa import LzsaDiskCPU
from test_fap3_disk import install
import compressed_sector_cache as cache
import inplace_slot_input_z80 as producer
import pipelined_frame_z80 as video

STOP,STACK,READ=0x100,0x9bf0,0x7800


def word(c,at,n=None):
    if n is None:return c.read8(at)+256*c.read8(at+1)
    c.write8(at,n);c.write8(at+1,n>>8)


class MockDisk(LzsaDiskCPU):
    def step(self):
        if self.pc!=READ:return super().step()
        assert word(self,self.disk['remaining'])>0
        region=self.read8(self.disk['write_region']);bank=region if region<2 else region+1
        self.port_7ffd=(self.port_7ffd&8)|16|bank;self.write8(video.SHADOW,self.port_7ffd)
        high=self.read8(self.disk['write_high'])
        for i,v in enumerate(self.source[self.reads]):self.write8(high*256+i,v)
        self.reads+=1;word(self,self.disk['remaining'],len(self.source)-self.reads)
        self.pc=self.pop();self.tstates+=10  # Only RET; physical read cost is excluded.


def fixture():
    c=MockDisk(b'',b'');c.source=[bytes((i*31+j*7)%256 for j in range(256)) for i in range(100)];c.reads=0
    c.disk=dict(remaining=0x6000,write_high=0x6002,write_region=0x6003)
    m=dict(producer_labels=dict(read_sector=READ,copy_sector=producer.COPY),disk_labels=c.disk)
    regions,labels,listing=cache.build(m)
    z=dict(block_length=0x6010,block_end=0x6012,input_pointer=0x6014,block_stored=0x6016)
    pr,_,pl=producer.build(z,c.disk|dict(disk_position=0x6018,read_one=READ))
    copy=[(a,b) for a,b in pr if a==producer.COPY]
    vr,_,vl=video.build_video(dict(saved_page=0x6020,screen_base=0x6021),{},dict(elapsed_fields=0x6022),irq_safe_paging=True)
    c.port_7ffd=0x17
    for at,data in regions+copy+vr:install(c,at,data)
    word(c,c.disk['remaining'],len(c.source));c.write8(video.SHADOW,0x17)
    rows={r['address']:r for r in listing+pl+vl}
    return c,labels,rows


def run(c,pc,rows):
    c.pc=pc;c.sp=STACK;c.push(STOP);before=c.tstates
    while c.pc!=STOP:
        pc,t=c.pc,c.tstates;c.step();elapsed=c.tstates-t
        if pc==READ:continue
        wanted=rows[pc]['tstates'];assert elapsed in (wanted if isinstance(wanted,list) else [wanted]),(rows[pc],elapsed)
    assert c.sp==STACK
    return c.tstates-before


def independent_hit(before,page,labels,expected,cycles):
    m=Z80Machine();m.memory[:]=bytes(65536);banks=[bytearray(b) for b in before];selected=[page&7]
    m.set_memory_block(0x4000,banks[5]);m.set_memory_block(0x8000,banks[2]);m.set_memory_block(0xc000,banks[selected[0]])
    def output(port,value):
        assert port==0x7ffd
        banks[selected[0]][:]=m.memory[0xc000:];selected[0]=value&7
        m.set_memory_block(0xc000,banks[selected[0]])
    m.set_output_callback(output);m.set_memory_block(STACK-2,STOP.to_bytes(2,'little'))
    m.sp=STACK-2;m.pc=labels['take_sector'];m.set_breakpoint(STOP)
    budget=50000;m.ticks_to_stop=budget
    while m.pc!=STOP:
        event=m.run();assert not event&m._TICKS_LIMIT_HIT
    assert budget-m.ticks_to_stop==cycles
    assert m.sp==STACK and selected[0]==page&7
    banks[selected[0]][:]=m.memory[0xc000:];banks[2][:]=m.memory[0x8000:0xc000];banks[5][:]=m.memory[0x4000:0x8000]
    for bank in range(8):
        # Caller stack scratch may contain different entry register values.
        if bank==2:
            assert banks[bank][:0x1b80]==expected[bank][:0x1b80]
            assert banks[bank][0x1bf0:]==expected[bank][0x1bf0:]
        else:assert banks[bank]==expected[bank],bank


class SectorCacheTests(unittest.TestCase):
    def test_fifo_wrap_full_empty_and_paging(self):
        c,l,rows=fixture();consumed=0;self.cycles=[];self.prefetch_cycles=[]
        # Fill, partially drain, wrap both cursors, consume after physical EOF.
        for fill,take in ((28,19),(19,35),(28,10),(17,36)):
            c.port_7ffd=0x17;c.write8(video.SHADOW,0x17)
            for _ in range(fill):
                if not word(c,c.disk['remaining']):break
                old=c.read8(l['write_index']);reads=c.reads;ticks=run(c,l['prefetch'],rows)
                self.prefetch_cycles.append(dict(write_index=old,read=c.reads!=reads,excluding_physical_read=ticks-10*(c.reads!=reads)))
                self.assertLessEqual(c.read8(l['count']),cache.SECTORS)
            if c.read8(l['count'])==cache.SECTORS:
                reads=c.reads;self.assertEqual(run(c,l['prefetch'],rows),44);self.assertEqual(c.reads,reads)
            for _ in range(take):
                if consumed==len(c.source):break
                bank=(0,1,3,4)[consumed%4];high=(0xbc,0xc0,0xef,0xff)[consumed%4]
                c.port_7ffd=16|bank;c.write8(video.SHADOW,c.port_7ffd)
                c.write8(c.disk['write_region'],bank if bank<2 else bank-1);c.write8(c.disk['write_high'],high)
                count=c.read8(l['count']);reads=c.reads;before=[bytes(b) for b in c.banks];page=c.port_7ffd
                ticks=run(c,l['take_sector'],rows)
                self.assertEqual(bytes(c.read8(high*256+i) for i in range(256)),c.source[consumed])
                self.assertEqual(c.port_7ffd,page);self.assertEqual(c.read8(l['count']),max(0,count-1))
                self.assertEqual(c.reads,reads+(not count))
                if count:independent_hit(before,page,l,[bytes(b) for b in c.banks],ticks)
                else:self.assertEqual(ticks,37)  # 27-T miss check + mocked physical RET.
                self.cycles.append(dict(cached=bool(count),destination=high,read_index=before[2][l['read_index']-0x8000],tstates=ticks))
                consumed+=1
        self.assertEqual(consumed,100);self.assertEqual(c.reads,100);self.assertEqual(c.read8(l['count']),0)
        c.port_7ffd=0x17;c.write8(video.SHADOW,0x17)
        self.assertEqual(run(c,l['prefetch'],rows),78)


if __name__=='__main__':unittest.main()
