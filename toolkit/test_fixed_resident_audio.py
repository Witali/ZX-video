"""Shared fixed AY trees, page-boundary flags, exact records and cycle deltas."""
import unittest
from z80 import Z80Machine

from ay_huffman_stream import encode
from benchmark_resident_audio_z80 import Harness,STACK,STOP
from test_resident_audio_z80 import record
import resident_audio_z80 as resident


def independent_fill(before,page,h,expected):
    m=Z80Machine();m.memory[:]=bytes(65536)
    m.set_memory_block(0x4000,before[5]);m.set_memory_block(0x8000,before[2]);m.set_memory_block(0xc000,before[page&7])
    def output(port,value):
        if port==0x7ffd:m.set_memory_block(0xc000,before[value&7])
        else:raise AssertionError(('unexpected independent output',hex(port)))
    m.set_output_callback(output)
    m.set_memory_block(STACK-2,STOP.to_bytes(2,'little'));m.sp=STACK-2;m.pc=h.bridge['labels']['fill']
    registers=('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl','ix','iy')
    for name in registers:setattr(m,name,0x9797)
    m.set_breakpoint(STOP);budget=2000000;m.ticks_to_stop=budget
    while m.pc!=STOP:
        event=m.run();assert not event&m._TICKS_LIMIT_HIT
    assert budget-m.ticks_to_stop==expected,(budget-m.ticks_to_stop,expected)
    assert m.sp==STACK and all(getattr(m,n)==0x9797 for n in registers)
    for region in h.build['regions']:
        at=region['address'];end=at+len(bytes.fromhex(region['data_hex']))
        assert bytes(m.memory[at:end])==bytes(h.cpu.banks[2][at-0x8000:end-0x8000])
    assert bytes(m.memory[0xa000:0xa400])==bytes(h.cpu.banks[2][0x2000:0x2400])


def data():
    return encode([record(2047,lambda r:(i*3+r*11)%80) for i in range(80)],bytes(range(11)))[0]


class FixedResidentAudioTests(unittest.TestCase):
    def test_one_bank_can_move_to_six_without_extra_cycles(self):
        blob=data();old=Harness(blob,paging=True,batch=31,fixed=True)
        new=Harness(blob,paging=True,batch=31,fixed=True,single_bank=6)
        self.assertEqual(new.build['banks'],[6])
        self.assertEqual(old.init_tstates,new.init_tstates)
        while old.consumed<len(old.records):
            a,n=old.fill_wrapped();before=[bytes(b) for b in new.cpu.banks];page=new.cpu.port_7ffd
            b,k=new.fill_wrapped();self.assertEqual((a,n),(b,k));independent_fill(before,page,new,b)
            for _ in range(n):old.consume();new.consume()
        old.finish();new.finish()
        with self.assertRaisesRegex(ValueError,'four video slots require one-bank AY'):
            Harness(blob,paging=True,fixed=True,single_bank=6,first_bank_bytes=1)

    def test_fixed_forest_has_identical_one_bank_cycles(self):
        blob=data();old=Harness(blob,paging=True,batch=31);new=Harness(blob,paging=True,batch=31,fixed=True)
        self.assertTrue(any(r['address']==0xb100 for r in new.build['regions']))
        self.assertEqual(old.init_tstates,new.init_tstates)
        while old.consumed<len(old.records):
            a,n=old.fill_wrapped();before=[bytes(b) for b in new.cpu.banks];page=new.cpu.port_7ffd
            b,k=new.fill_wrapped();self.assertEqual((a,n),(b,k));independent_fill(before,page,new,b)
            for _ in range(n):old.consume();new.consume()
        old.finish();new.finish()

    def test_spanning_payload_and_exact_boundary_cycle_formula(self):
        blob=data();payload=resident.tables(blob)[3]
        for limit in (1,33,len(payload)-1):
            old=Harness(blob,paging=True,batch=31,fixed=True)
            new=Harness(blob,paging=True,batch=31,fixed=True,first_bank_bytes=limit)
            self.assertEqual(new.init_tstates-old.init_tstates,20)
            while old.consumed<len(old.records):
                a,n=old.fill_wrapped();first=len(new.cpu.payload_reads)
                before=[bytes(bank) for bank in new.cpu.banks];page=new.cpu.port_7ffd
                b,k=new.fill_wrapped();reads=new.cpu.payload_reads[first:]
                extra=6+28*len(reads)+186*reads.count((4,65535))+27*reads.count((6,65535))
                self.assertEqual((b-a,k),(extra,n));independent_fill(before,page,new,b)
                for _ in range(n):old.consume();new.consume()
            old.finish();new.finish()
            self.assertEqual(new.fill_wrapped()[0]-old.fill_wrapped()[0],6)

    def test_interrupts_across_source_bank_change(self):
        # One-record batches keep the per-call instruction guard meaningful
        # under the intentionally unrealistic IRQ-after-every-instruction load.
        h=Harness(data(),paging=True,batch=1,fixed=True,first_bank_bytes=1)
        while h.cpu.published<len(h.records):h.fill_wrapped(h.interrupt)
        while h.consumed<len(h.records):h.consume()
        h.finish();self.assertGreater(h.cpu.irq_count,1000)


if __name__=='__main__':unittest.main()
