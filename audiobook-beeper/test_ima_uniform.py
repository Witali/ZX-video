"""Validate guarded data, untaken returns, and exact uniform instruction timing."""
import json
import unittest

from z80 import Z80Machine

from ima_codec import STEPS,transition,require_unclipped
from ima_player import program,layout,ORIGIN,build_disk


class UniformTests(unittest.TestCase):
    def test_both_nibbles_all_safe_transitions(self):
        sections,_=layout();blob,meta=program(sections,uniform=True)
        labels=meta['player_labels'];checked=0
        for half,finish in (('low','high'),('high','low')):
            for predictor in (-32768,-12000,0,12000,32767):
                for index,step in enumerate(STEPS):
                    for code in range(16):
                        delta=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
                        raw=predictor+(-delta if code&8 else delta)
                        if not -32768<=raw<=32767:continue
                        m=Z80Machine();m.memory[:]=b'\xa5'*65536
                        m.set_memory_block(ORIGIN,blob)
                        m.pc=labels[half];m.bc=0x10fe;m.de=0x8000;m.hl=0xc040
                        m.alt_af=0x8000;m.af=0xffff;m.ix=predictor+32768
                        m.alt_hl=meta['table_base']+64*index;m.sp=0x6000
                        m.memory[0xc040]=code if half=='low' else code<<4
                        before=bytes(m.memory);times=[]
                        m.set_breakpoint(labels[finish]);m.ticks_to_stop=1000
                        def output(port,value):
                            self.assertEqual(port,0x10fe);self.assertEqual(value&15,0)
                            times.append(1000-m.ticks_to_stop)
                        m.set_output_callback(output)
                        while m.pc!=labels[finish]:
                            if m.run()&m._TICKS_LIMIT_HIT:self.fail('unexpected RET or decode stall')
                        wanted,state=transition(predictor,index,code)
                        self.assertEqual(m.ix,wanted+32768);self.assertEqual(m.d,(wanted+32768)>>8)
                        self.assertEqual(m.alt_hl,meta['table_base']+64*state)
                        self.assertEqual(len(times),6);self.assertEqual([b-a for a,b in zip(times,times[1:])],[73]*5)
                        self.assertEqual(1000-m.ticks_to_stop,438);self.assertEqual(bytes(m.memory),before)
                        checked+=1
        print(json.dumps(dict(safe_native_transitions_both_halves=checked)),flush=True)

    def test_guard_rejects_clipping_before_assembly(self):
        for data,predictor in ((bytes([7]),32760),(bytes([143]),-32761)):
            with self.assertRaisesRegex(ValueError,'requires saturation'):require_unclipped(data,predictor,0)
        sections,_=layout();size=sum(s['bytes'] for s in sections)
        with self.assertRaisesRegex(ValueError,'requires saturation'):
            build_disk(b'\x77'*size,uniform=True)
        guard=require_unclipped(b'\0'*size)
        self.assertEqual(guard['samples'],size*2);self.assertEqual(guard['raw_max'],0)


if __name__=='__main__':unittest.main()
